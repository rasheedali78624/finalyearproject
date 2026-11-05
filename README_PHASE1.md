# Phase 1: baseline detection on MQTTset (Objective O1)

This folder trains and evaluates three machine-learning intrusion detectors on
the MQTTset dataset, honestly measuring how train/test duplication inflates
their scores.

## What you need

- The three MQTTset files in
  `~/Downloads/P1/Datasets/MQTTset/Data/FINAL_CSV/`:
  `mqttdataset_reduced.csv`, `train70_reduced.csv`, `test30_reduced.csv`.
  They are only read, never changed.
- The virtual environment with pandas, scikit-learn, xgboost, matplotlib.
- If the data is somewhere else: `export MQTT_DATA_DIR=/path/to/FINAL_CSV`

## Run everything

Run these from this folder, in every new Terminal window:

```bash
source ~/Downloads/P1/.venv/bin/activate
python3 src/run_phase1.py
```

Faster version (cross-validation once instead of three times):

```bash
python3 src/run_phase1.py --repeats 1
```

Run single steps on their own:

```bash
python3 src/dedup_analysis.py          # Task 1: duplication and leakage, raw files
python3 src/feature_space_analysis.py  # Step 2: re-measure on the 20 model features
```

If XGBoost fails with a `libomp` error: `brew install libomp`.

## What each file does

| File | Job |
|---|---|
| `src/config.py` | Paths, seed (42), constants, encoding choices |
| `src/utils.py` | Logging, saving tables, exact row keys |
| `src/dedup_analysis.py` | Task 1: duplicates, label conflicts, error floor, leakage on raw data |
| `src/data_loader.py` | Encoding rules; builds Variant A and Variant B |
| `src/feature_space_analysis.py` | Step 2: the same measurements on the final features |
| `src/models.py` | Random Forest, XGBoost, MLP with the brief's settings |
| `src/evaluate.py` | Metrics, latency, model size, plots |
| `src/run_phase1.py` | Runs everything end to end |

## Outputs

All outputs go to `results/phase1/`:

- `tables/` (CSV and Markdown)
- `figures/` (PNG, 160 dpi)
- `models/` (saved `.joblib`, not committed)
- `logs/` (a full timestamped log of every run)

A run also writes `requirements.txt` with the exact package versions it used,
and `results/phase1/PHASE1_RESULTS_AUTO.md` with all result tables.

## Key design decisions

- **Variant A**: the published `train70`/`test30` split, unchanged.
- **Variant B**: one row per (feature vector, label), split 70/30 with
  `StratifiedGroupKFold` so identical feature vectors never sit on both sides.
  Its cross-validation is grouped the same way.
- **Features**: 20 = 33 − 12 constant − `mqtt.msg`. Hex fields become integers,
  and a plain `0` ("field absent") becomes −1, kept apart from a real 0.
- **Imbalance**: balanced class weights for all three models. No SMOTE, because
  synthetic packets may not be valid MQTT.
- **Headline metric**: macro F1. Accuracy is reported but never as the headline.
- **Reproducibility**: seed 42 everywhere. Every number except the timing
  numbers (latency, training time) should be identical on re-run on the same
  machine and library versions.
