# Project Handoff — read this first

**For:** a fresh assistant session with no prior context.
**Updated:** 15 November 2026. **Branch:** `claude/friendly-dijkstra-0h6cpk` (continues `claude/amazing-hopper-glemny`).

This repository is a Master of Cyber Security research project. Objectives O1–O4
are all implemented and have run on the real data. This document is the complete
state so a new session can continue without re-deriving anything.

---

## 1. The person and how to work with them

- **Rasheed Ali Saadik Ali**, matric 23089292, MSc Cyber Security, Universiti
  Malaya. Supervisor **Dr. Bryan Raj** (meets Mondays). Panel examiner **Prof.
  Dr. Mohd Yamani Idna Idris** (IoT, pattern recognition, adversarial ML).
- **Not a strong programmer.** Explain what code does in plain words. Walk
  through one step at a time; he stalls when given a menu of open choices, so
  recommend one clear path. He learns by doing, then running it himself.
- **He must be able to defend every number.** He was previously penalised for
  presenting figures and citations he had not verified. So: **never fabricate,
  estimate or placeholder a number.** Every figure must come from code that ran.
  Label anything uncertain as uncertain. Teaching examples must be marked as
  invented ("pretend numbers").
- He wants reasoning shown, pushes back, and that is welcome.

## 2. Hard constraints (do not break)

- **CPU only**, no GPU. Deep learning stays small (shallow MLP at most).
- **Never report plain accuracy as the headline** — the data is ~270:1
  imbalanced. Use **macro F1** and per-class recall.
- **Do not modify the raw dataset files.** All transforms happen in code.
- **Fix all seeds (42) and record library versions.**
- **No SMOTE / synthetic oversampling** without discussion — synthetic MQTT
  packets may not be protocol-valid, which contradicts the project's argument.

## 3. The research in one paragraph

Published ML intrusion detectors for MQTT report 97–99% accuracy, but against a
passive attacker unaware a detector exists. This project tests whether that
survives an **adaptive, constraint-limited** attacker (one who may only change
MQTT fields while keeping the packet valid and the attack working), then builds
a defence. Four objectives:

- **O1** baseline detection on MQTTset (done).
- **O2** constraint-aware adversarial evasion attacks (done).
- **O3** a robust detection framework, evaluated under adaptive re-attack (done).
- **O4** robustness vs accuracy vs computational-cost trade-off (done).

## 4. Environment and data

- Mac: project root `~/Downloads/P1`, virtualenv `~/Downloads/P1/.venv`
  (activate with `source ~/Downloads/P1/.venv/bin/activate` in every terminal).
  Repo clone at `~/Downloads/P1/finalyearproject`.
- Data (MQTTset) lives on the Mac at
  `~/Downloads/P1/Datasets/MQTTset/Data/FINAL_CSV/` — `mqttdataset_reduced.csv`
  (full), `train70_reduced.csv`, `test30_reduced.csv`. **Not committed** (public
  benchmark, large). A cloud session can point to a copy with
  `export MQTT_DATA_DIR=/path/to/FINAL_CSV`.
- If `xgboost` fails to import on Mac with a `libomp` error: `brew install libomp`.
- Libraries pinned in `requirements.txt` (numpy 2.5.4, pandas 3.0.6,
  scikit-learn 1.9.1, xgboost 3.4.1, matplotlib 3.11.2, joblib 1.6.0).

## 5. Key dataset facts (measured)

- 330,926 rows, label column `target`, 6 classes: legitimate 50%, dos 39.35%,
  bruteforce 4.38%, malformed 3.30%, slowite 2.78%, flood 0.19% (613 rows).
- 12 columns are constant → dropped. `mqtt.msg` dropped (payload, 50k values,
  memorisable, attacker-controlled, and a `slowite` giveaway). **20 features
  remain.**
- Two dataset variants: **A** = published split (has 69.59% train/test leakage);
  **B** = de-duplicated + grouped/stratified split (leak-free, the honest one).
  O2–O4 target models trained on **Variant B**.

## 6. What is done, with the key numbers

O1 numbers are from cloud runs on verified-identical data, reproduced exactly
on the Mac. **O2–O4 numbers are from the Mac run of 16 Nov 2026 with corrected
attack rules** (`docs/phase2/mac_run_20261116/`). The 15 Nov numbers (RF 4.9%,
XGBoost 29.3%, MLP 75.2%) are **withdrawn**: `src/o2_validity_audit.py` showed
most of those evasions changed rows an attacker cannot reshape (bare TCP rows,
broker replies, fixed-length packets). Never quote them.

**O1 (Phase 1):** XGBoost is best. Macro F1 on Variant B: XGBoost 0.8673, RF
0.8559, MLP 0.8030. On MQTT-only packets, XGBoost reaches 0.979. Full detail in
`docs/phase1/PHASE1_FINDINGS.md`. Train-vs-test gaps (overfitting check):
XGBoost 0.0050, MLP 0.0056, RF 0.0482 (`docs/phase1/OVERFITTING_CHECK.md`).

**O2 (attacks):** only client-sent MQTT packets are attacked. Mean attack
success over five classes, report set: **RF 10.83%, XGBoost 16.48%, MLP
80.72%**. For the tree models this is almost all the `malformed` class (RF
51.22%, XGBoost 82.04%); without `malformed` the means are RF 0.73%, XGBoost
0.09%, MLP 76.21%. Always give both. `docs/phase2/O2_O4_FINDINGS.md`.

**O3 (defence):** adversarial training, adaptive re-attack, report set:
XGBoost 16.48% → 0.39%, MLP 80.72% → 6.64%, RF 10.83% → 6.79%; clean macro F1
moves by at most 0.002. Feature hardening gives no consistent benefit.

**O4 (trade-off):** XGBoost adversarially trained is the best operating point —
clean F1 0.8688, robustness 99.58%, 1.1 MB, 0.106 ms/packet (Mac). Figure
`results/phase1/figures/o4_tradeoff.png`.

## 7. File map (`src/`)

| File | Role |
|---|---|
| `config.py` | paths, seed, constants, encoding + model/eval settings |
| `utils.py` | logging, table saving (`subdir=` picks results/phaseN/tables) |
| `data_loader.py` | encoding rules; builds Variant A and Variant B |
| `dedup_analysis.py` | O1 Task 1: duplication, leakage, label conflicts (raw) |
| `feature_space_analysis.py` | O1 Step 2: same, on the 20 model features |
| `mqtt_only_analysis.py` | MQTT-packets-only population analysis |
| `models.py` | Random Forest, XGBoost, MLP with report settings |
| `evaluate.py` | metrics, latency, model size, plots |
| `run_phase1.py` | runs all of O1 end to end |
| `sensitivity_checks.py` | class-weighting + memorisation/ambiguity checks |
| `overfitting_check.py` | train vs test score per model (panel's overfitting comment); findings in `docs/phase1/OVERFITTING_CHECK.md` |
| `constraints.py` | **O2/O3 shared**: constraint set + protocol-validity checker |
| `o2_validity_audit.py` | sorts saved evasions by packet type (attacker-sent / broker reply / bare TCP / impossible length); run after every O2 run |
| `phase2_attacks.py` | **O2** attack + evaluation |
| `phase3_defence.py` | **O3** adversarial training + adaptive re-attack |
| `phase4_tradeoff.py` | **O4** robustness/accuracy/cost table + figure |
| `run_phase2to4.py` | runs O2→O3→O4 end to end |
| `mosquitto_testbed/` | live-broker protocol-validity check (Mac only) |

## 8. How to run (on the Mac)

```bash
cd ~/Downloads/P1/finalyearproject
source ~/Downloads/P1/.venv/bin/activate
git pull
python3 src/run_phase1.py        # O1 (~10 min)
python3 src/run_phase2to4.py     # O2, O3, O4 (~25 min)
```
Then `mosquitto_testbed/README.md` for the broker validity check.
Outputs go to `results/phaseN/tables`, `results/phase1/figures`, `results/phase1/logs`.

## 9. Documents to read (in order)

1. `docs/phase1/study_guide.html` — plain-language guide to the whole project
   (also a private web page; ask Rasheed for the link if needed).
2. `docs/phase1/PHASE1_FINDINGS.md`, `STEP2_FINDINGS.md`, `TASK1_FINDINGS.md`.
3. `docs/PROJECT_DIRECTION_REVIEW.md` — what to change after Phase 1.
4. `docs/phase2/CONSTRAINT_TABLE.md` — the 20-feature constraint table.
5. `docs/phase2/O2_O4_DESIGN.md` then `O2_O4_FINDINGS.md` — the attack/defence work.
6. `papers/PAPER_SCAN.md` — review of the 26 reference papers (which datasets).
7. `docs/P1_Research_Report_*.pdf` and `docs/Panel_QnA_Prof_Yamani.pdf` — the
   submitted report and the anticipated viva questions.

## 10. Open decisions / next steps

- **Panel comments (26 Aug) were: too ambitious/prioritise; study the data
  (balance, overfitting).** No further datasets are planned; ask Dr. Bryan to
  move MQTT-IoT-IDS2020 (named in the report as secondary dataset) to future work.
- **Decide with Dr. Bryan:** whether to run all of O2–O4 on the **MQTT-only**
  population as well as all-rows Variant B (direction review recommends it;
  not yet done). This is the main open modelling choice.
- Four Phase-1 decisions still to confirm with Dr. Bryan: headline framing,
  class weighting, dropping `mqtt.msg`, the small `flood` class (see
  `PHASE1_FINDINGS.md` §6).
- Mosquitto validity check: not run. `mosquitto_testbed/replay_check.py` counts a
  packet as accepted once sent, without waiting for the broker's reply; rewrite
  it before use. Mosquitto is not yet installed on the Mac (`brew install mosquitto`).
- O2–O4 are single-seed runs: no confidence intervals yet.
- Bare TCP rows are excluded from the attack (sender unknown); tell Dr. Bryan.
- Report corrections needed (see `CONSTRAINT_TABLE.md` and direction review):
  33→20 features, 7→6 text columns, 22.6%→69.59% leakage, `mqtt.conflags` and
  `tcp.len` are *dependent* not immutable/mutable.
- Read-in-full reading list for the literature comparison: papers 15 and 23, the
  original MQTTset paper (Vaccari 2020), Zeghida 2023, Prajisha & Vasudevan 2022.

## 11. Git / attribution

- Develop on the branch the current session is assigned (latest: `claude/friendly-dijkstra-0h6cpk`), commit and push there.
- The cloud session's `.git/info/exclude` hides `results/` and the dataset; the
  Mac run regenerates results locally.
- End commit messages with the Co-Authored-By / Claude-Session lines the harness
  provides in each session (they change per session; use the current ones).
