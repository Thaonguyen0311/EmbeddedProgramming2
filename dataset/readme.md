# Dataset

The complete cleaned combined dataset is included in this repository under `dataset/cleaned_data/` (about 1.1 MB); no external data location is needed.

| Split | Relax rows | Stressed rows |
| --- | ---: | ---: |
| Training | 17,834 | 12,286 |
| Testing | 4,060 | 5,869 |

Rows come from PPG/GSR recordings collected by Thao Nguyen and Seonmi Wu. The source recordings were labeled Relax or Stressed; each numeric row is one sample. Column A is elapsed time in milliseconds and column B is raw PPG. Other sensor columns are retained, but the current classifier uses only raw PPG.

The cleaned files omit rows with PPG below 10,000 and remove sharp local drops below 70% of a roughly one-second neighboring average. These are dataset-specific cleaning rules, not universal sensor thresholds. File names are retained in the source_file column for traceability; review or replace them with participant IDs before any wider public sharing.
