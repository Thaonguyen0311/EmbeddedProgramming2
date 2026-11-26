# Project report — PPG-based stress classification

**Team:** Thao Nguyen, Seonmi Wu

## What it does

The project explores whether raw optical PPG readings can distinguish recordings labeled Relax from recordings labeled Stressed. An ESP32-S3 reads PPG and GSR sensors and reports a smoothed Relax/Stressed status from the PPG signal. The output is an experimental label, not a medical diagnosis or evidence that someone is lying.

## How it works

OB1203 PPG and GSR Click readings are collected by the ESP32-S3 at a nominal 50 Hz and streamed as CSV. The Python training script treats each valid row as one sample and fits a 250-tree Random Forest using column B (ppg_raw) as its single feature; column A is timing only. The compact model header is included by the detection sketch, which classifies valid PPG readings and uses a 25-row majority vote before printing stress_state. GSR is recorded but is not used by this model.

## Data

Thao Nguyen and Seonmi Wu collected the sensor recordings together. The final dataset uses Relax/Stressed labels; the original data-plan template proposed truthful/deceptive labels, but the implemented model does not classify truthfulness. After cleaning, training contains 17,834 Relax rows and 12,286 Stressed rows; testing contains 4,060 Relax rows and 5,869 Stressed rows. One row is one example. All four combined CSVs are included under dataset/cleaned_data/ (about 1.1 MB). Rows below 10,000 PPG were removed as likely finger-off readings; sharp drops below 70% of the nearby one-second average were also removed from combined files.

## Results — honestly

The supplied confusion matrix summarizes 9,929 held-out test rows. It shows 3,781 Relax and 5,097 Stressed rows classified correctly, with 279 Relax rows labeled Stressed and 772 Stressed rows labeled Relax.

| Actual label | Predicted Relax | Predicted Stressed |
| --- | ---: | ---: |
| Relax | 3,781 | 279 |
| Stressed | 772 | 5,097 |

![Confusion matrix — PPG stress classifier](confusion_matrix.png)

Accuracy is 89.4%; Relax recall is 93.1%; Stressed precision is 94.8%; and Stressed recall is 86.9%. These are row-level results from the supplied test matrix. Neighboring rows are correlated, and the on-device 25-row vote was not separately evaluated in this matrix, so these numbers do not establish performance on new people.

## The two sentences

- **Platform:** ESP32-S3 DevKitC-1 with Arduino and PlatformIO, chosen to read the OB1203 PPG and GSR sensors and run the compact classifier on the board.
- **Threat model:** Asset physiological readings and class labels · threat disclosure of linkable sensor recordings or treating a noisy output as a definitive assessment · response minimize identifiers, validate readings, and limit use to an educational research demo.

## What was hard, and what we'd do next

Raw PPG changes with finger contact, movement, and personal baseline, so cleaning out finger-off periods was important. The model uses one raw sensor value rather than pulse timing or variability, and the rows are not independent. With more time, we would collect more participants, test on people excluded from training, add GSR and reliable heart-rate-variability features, and evaluate the smoothed on-device output separately.

## Who did what

- **Thao Nguyen:** Led the project implementation, data cleaning, model training and evaluation, and report; collected sensor recordings with Seonmi.
- **Seonmi Wu:** Helped Thao collect the sensor recordings used for the Relax and Stressed data.

## AI use

ChatGPT assisted with Python training and data-cleaning code, debugging CSV formats, interpreting the confusion matrix, and editing the report. Thao reviewed the code and outputs; the team remains responsible for the data, labels, and conclusions.
