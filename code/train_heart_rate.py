#!/usr/bin/env python3
"""Train a row-level raw PPG stress classifier and export it as a C/C++ header.

Training rows are read from data/training/{relax,stressed}/*.csv. Testing can
use data/testing/{relax,stressed}/*.csv or root-level *_combined.csv files.
Each numeric CSV row is one example; A is timestamp and B is ppg_raw.
"""
from __future__ import annotations
import argparse
import csv
import math
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

LABELS = {"relax": 0, "stressed": 1}

def parse_letter(value: str) -> int:
    value = value.strip().upper()
    if not value.isalpha():
        raise argparse.ArgumentTypeError("Column must be an Excel letter such as A or B")
    n = 0
    for ch in value:
        n = n * 26 + ord(ch) - 64
    return n - 1

def read_rows(path: Path, time_col: int, ppg_col: int, min_ppg: float):
    samples = []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        for row in csv.reader(f):
            if len(row) <= max(time_col, ppg_col):
                continue
            try:
                timestamp = float(row[time_col].strip())
                ppg_raw = float(row[ppg_col].strip())
            except (ValueError, TypeError):
                continue
            if math.isfinite(timestamp) and math.isfinite(ppg_raw) and ppg_raw >= min_ppg:
                samples.append(ppg_raw)
    return samples

def collect(root: Path, split: str, time_col: int, ppg_col: int, min_ppg: float):
    X, y = [], []
    split_root = root / split
    for label_name, label in LABELS.items():
        combined_file = split_root / f"{label_name}_combined.csv"
        label_folder = split_root / label_name
        # Prefer a combined CSV when present, avoiding duplicate rows.
        if combined_file.is_file():
            paths = [combined_file]
        elif label_folder.is_dir():
            paths = sorted(label_folder.glob("*.csv"))
        else:
            paths = []
        for path in paths:
            samples = read_rows(path, time_col, ppg_col, min_ppg)
            X.extend([[value] for value in samples])
            y.extend([label] * len(samples))
            print(f"{split}: {path.name} [{label_name}]: {len(samples)} row samples")
    return np.asarray(X, dtype=float).reshape(-1, 1), np.asarray(y, dtype=int)

def c_float(value: float) -> str:
    """Format a Python float as a valid C float literal."""
    result = format(float(value), ".9g")
    if "." not in result and "e" not in result.lower():
        result += ".0"
    return result + "f"

def export_c_header(model: RandomForestClassifier, path: Path):
    """Export an equivalent compact 1-D integer-input classifier for ESP32."""
    if list(model.classes_) != [0, 1]:
        raise ValueError("Header export expects class labels 0 (relax) and 1 (stressed).")

    # Each tree is a piecewise-constant function of one integer PPG value.
    # Sweep its leaf intervals across the forest and retain only points where
    # the forest's majority-vote label changes. This avoids a huge node table.
    max_ppg = (1 << 24) - 1  # OB1203 PPG samples are 24-bit values.
    events = []
    for estimator in model.estimators_:
        tree = estimator.tree_
        def add_leaf_events(node: int, low: int, high: int):
            left = int(tree.children_left[node])
            if left < 0:
                class_index = int(np.argmax(tree.value[node][0]))
                label = int(model.classes_[class_index])
                events.append((low, label, 1))
                events.append((high + 1, label, -1))
                return
            if tree.feature[node] != 0:
                raise ValueError("Header export supports the single ppg_raw feature only.")
            cut = math.floor(float(tree.threshold[node]))
            left_high = min(high, cut)
            right_low = max(low, cut + 1)
            if low <= left_high:
                add_leaf_events(left, low, left_high)
            if right_low <= high:
                add_leaf_events(int(tree.children_right[node]), right_low, high)
        add_leaf_events(0, 0, max_ppg)

    events.sort(key=lambda event: event[0])
    votes = [0, 0]
    initial_label = None
    previous_label = None
    boundaries, labels = [], []
    i = 0
    while i < len(events):
        point = events[i][0]
        while i < len(events) and events[i][0] == point:
            _, label, delta = events[i]
            votes[label] += delta
            i += 1
        if point > max_ppg:
            continue
        current_label = 1 if votes[1] > votes[0] else 0
        if previous_label is None:
            initial_label = current_label
        elif current_label != previous_label:
            boundaries.append(point)
            labels.append(current_label)
        previous_label = current_label
    if initial_label is None:
        raise ValueError("Could not derive forest decision regions.")

    def write_array(f, c_type: str, name: str, values):
        f.write(f"static const {c_type} {name}[{max(1, len(values))}] = {{\n    ")
        if values:
            for index, value in enumerate(values):
                if index:
                    f.write(", " if index % 12 else ",\n    ")
                f.write(str(value))
        else:
            f.write("0")
        f.write("\n};\n\n")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("// Generated compact forest decision regions; do not edit by hand.\n")
        f.write("#pragma once\n#include <stdint.h>\n#include <stddef.h>\n\n")
        f.write("#define PPG_STRESS_RELAX 0\n#define PPG_STRESS_STRESSED 1\n")
        f.write(f"#define PPG_STRESS_REGION_COUNT {len(boundaries) + 1}\n\n")
        write_array(f, "uint32_t", "ppg_stress_boundaries", boundaries)
        write_array(f, "uint8_t", "ppg_stress_region_labels", [initial_label] + labels)
        f.write("static inline int ppg_stress_predict(float ppg_raw) {\n")
        f.write("    size_t low = 0, high = PPG_STRESS_REGION_COUNT - 1;\n")
        f.write("    while (low < high) {\n")
        f.write("        const size_t mid = low + (high - low) / 2;\n")
        f.write("        if (ppg_raw < (float)ppg_stress_boundaries[mid]) high = mid;\n")
        f.write("        else low = mid + 1;\n    }\n")
        f.write("    return ppg_stress_region_labels[low];\n}\n\n")
        f.write("static inline const char* ppg_stress_label_name(int label) {\n")
        f.write("    return label == PPG_STRESS_STRESSED ? \"Stressed\" : \"Relax\";\n}\n")
    print(f"Compact C header: {len(boundaries) + 1} decision regions")
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent.parent / "dataset" / "cleaned_data",
                    help="folder containing training/ and testing/")
    ap.add_argument("--time-column", default="A", help="timestamp column (default A; used to identify rows)")
    ap.add_argument("--ppg-column", default="B", help="raw PPG column (default B)")
    ap.add_argument("--min-ppg", type=float, default=10000,
                    help="discard rows below this raw PPG cutoff (default 10000; use 0 to disable)")
    ap.add_argument("--header-out", type=Path, default=Path(__file__).resolve().parent / "ppg_stress_model.h",
                    help="output C/C++ header path")
    args = ap.parse_args()

    start = time.perf_counter()
    X_train, y_train = collect(args.data_dir, "training", parse_letter(args.time_column),
                               parse_letter(args.ppg_column), args.min_ppg)
    X_test, y_test = collect(args.data_dir, "testing", parse_letter(args.time_column),
                             parse_letter(args.ppg_column), args.min_ppg)
    if not len(X_train) or len(np.unique(y_train)) < 2:
        raise SystemExit("Need usable row samples in both training/relax and training/stressed.")

    model = RandomForestClassifier(n_estimators=250, min_samples_leaf=2,
                                   class_weight="balanced", random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    print(f"\nElapsed time (CSV loading and model fitting): {time.perf_counter() - start:.2f} seconds")
    print(f"Training row samples: {len(X_train)}; features per sample: 1 (ppg_raw)")
    if len(X_test):
        print(f"\nHeld-out test results ({len(X_test)} row samples):")
        print(classification_report(y_test, model.predict(X_test), target_names=["relax", "stressed"], zero_division=0))
        print("Confusion matrix (rows=true, columns=predicted):\n",
              confusion_matrix(y_test, model.predict(X_test), labels=[0, 1]))
    else:
        print("No usable test row samples found; skipping test metrics.")

    export_c_header(model, args.header_out)
    print(f"Saved ESP32 C/C++ model header: {args.header_out.resolve()}")

if __name__ == "__main__":
    main()




