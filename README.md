# PPG stress classifier

This team project uses an ESP32-S3 and optical PPG readings to classify sensor rows as Relax or Stressed. It is an educational prototype, not a lie detector or medical device. The classifier uses raw PPG only; GSR is recorded by the collection sketch but is not a model feature.

**Platform:** ESP32-S3 DevKitC-1 with Arduino and PlatformIO, chosen to read the OB1203 PPG and GSR sensors and run the compact classifier on the board.

See [report.md](report.md) for the method, held-out results, limitations, team contributions, and AI use.

## Repository contents

- `code/` — sensor sketches, training script, and ESP32 model header.
- `dataset/cleaned_data/` — combined cleaned training and testing CSV files.
- `confusion_matrix.png` — test-set confusion matrix used in the report.

## Train and export the model

From the repository root, install Python dependencies and run:

~~~powershell
python -m pip install numpy scikit-learn
python code/train_heart_rate.py
~~~

The script reads `dataset/cleaned_data/`, prints test metrics, and writes `code/ppg_stress_model.h`, which the detection sketch includes. Override paths with `--data-dir` or `--header-out` when needed.
