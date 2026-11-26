#!/usr/bin/env python3
"""Train a row-level stress classifier from raw PPG.

Expected layout: data/training/{relax,stressed}/*.csv and data/testing/{relax_combined,stressed_combined}.csv
Each numeric CSV row is one example. Column A is timestamp, column B is ppg_raw.
Folder or combined filename supplies the label; timestamp is not a model feature.
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
                continue  # Skip ESP32 boot text, headers, and nonnumeric rows.
            if math.isfinite(timestamp) and math.isfinite(ppg_raw) and ppg_raw >= min_ppg:
                samples.append(ppg_raw)
    return samples

def collect(root: Path, split: str, time_col: int, ppg_col: int, min_ppg: float):
    X, y = [], []
    split_root = root / split
    for label_name, label in LABELS.items():
        combined_file = split_root / f"{label_name}_combined.csv"
        label_folder = split_root / label_name
        # Prefer a combined CSV when present, so its rows are not counted twice
        # alongside the original per-recording files.
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

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent,
                    help="folder containing training/ and testing/")
    ap.add_argument("--time-column", default="A", help="timestamp column (default A; used to identify data rows)")
    ap.add_argument("--ppg-column", default="B", help="raw PPG column (default B)")
    ap.add_argument("--min-ppg", type=float, default=10000,
                    help="discard rows with ppg_raw below this cutoff (default 10000; use 0 to disable)")
    ap.add_argument("--model-out", type=Path, default=Path("ppg_stress_model.joblib"))
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
    try:
        import joblib
        args.model_out.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, args.model_out)
        print(f"Saved model: {args.model_out.resolve()}")
    except ImportError:
        print("Install joblib (normally included with scikit-learn) to save the model.")

if __name__ == "__main__":
    main()


