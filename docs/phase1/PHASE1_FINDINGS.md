# Phase 1 Findings — Baseline Detection on MQTTset (Objective O1)

**Status: confirmed on Rasheed's MacBook, 5 Nov 2026.** The main results and
cost figures below are from the **Mac run** (official). The sensitivity checks
(§3) are from the cloud run on identical copies of the data; they still need
re-running on the Mac (see §7).

| Run | Log | Machine | Settings |
|---|---|---|---|
| **Main pipeline (official)** | `mac_run_20261105/phase1_run_20261105_144354.txt` | MacBook Pro, Apple Silicon, 10 cores, macOS 27.0.1 | 5-fold CV × 3 repeats, seed 42; **10.5 min** |
| Main pipeline (cloud check) | `cloud_run_20261105/logs/phase1_run_20261105_060455.txt` | Linux, 4 cores | Same settings; 28.8 min |
| Sensitivity checks (cloud) | `cloud_run_20261105/logs/sensitivity_checks_20261105_060638.txt` | Linux, 4 cores | Class weighting on/off; Variant A test-row groups |

Libraries on the Mac: Python 3.14.2, numpy 2.5.4, pandas 3.0.6, scikit-learn
1.9.1, xgboost 3.4.1.

**Reproducibility across machines:**
- **Random Forest and XGBoost, both variants: every cross-validation and test
  number is identical** on the Mac and in the cloud.
- **MLP on Variant B: identical.**
- **MLP on Variant A: different.** Test macro F1 is 0.5837 on the Mac against
  0.5410 in the cloud; CV is 0.5786 ± 0.0399 against 0.5716 ± 0.0302. The cloud
  gave the same MLP result on two separate runs; the Mac has been run once so
  far. The
  likely cause is tiny floating-point differences between Apple Silicon and Intel
  maths libraries: the MLP training on Variant A is unstable (it has the largest
  fold-to-fold spread of any model), so small differences grow. This is an
  explanation, not a measurement. **The Mac figures are the official ones.**

---

## 1. What was run

- **Data:** `mqttdataset_reduced.csv` and its published split
  (`train70_reduced.csv` / `test30_reduced.csv`). Raw files only read.
- **Features: 20.** That is 33 minus 12 constant columns minus `mqtt.msg`
  (Step 2 findings §1, §3).
- **Variant A, as published:** train 231,646 / test 99,290 rows.
- **Variant B, de-duplicated:** one row per (feature vector, label), grouped
  and stratified 70/30 split. Train 76,276 / test 32,697 rows; no feature vector
  is on both sides. Cross-validation on B is grouped the same way.
- **Models:**
  - Random Forest (100 trees)
  - XGBoost (hist)
  - MLP (64-32, scaled inputs)
  - All three use balanced class weights; no oversampling.
- **Protocol:** cross-validation on the training set only (mean ± standard
  deviation over 15 folds), then **one** evaluation on the held-out test set.

## 2. Main results (held-out test set)

| Variant | Model | CV macro F1 | **Test macro F1** | Weighted F1 | Accuracy | FPR |
|---|---|---|---|---|---|---|
| A | Random Forest | 0.6206 ± 0.0030 | **0.6094** | 0.8812 | 0.8457 | 0.1445 |
| A | XGBoost | 0.6267 ± 0.0027 | **0.6164** | 0.8829 | 0.8470 | 0.1453 |
| A | MLP | 0.5786 ± 0.0399 | **0.5837** | 0.7602 | 0.6551 | 0.3734 |
| B | Random Forest | 0.8553 ± 0.0178 | **0.8559** | 0.9720 | 0.9715 | 0.0066 |
| B | XGBoost | 0.8662 ± 0.0174 | **0.8673** | 0.9737 | 0.9731 | 0.0122 |
| B | MLP | 0.8005 ± 0.0247 | **0.8030** | 0.9576 | 0.9556 | 0.0564 |

FPR = share of `legitimate` test rows flagged as any attack.

- **XGBoost is the best model on both variants.** Random Forest is close behind
  and the MLP is clearly weaker.
- Cross-validation and test scores agree closely, so the test sets are not
  unusually easy or hard.
- The MLP on Variant A is unstable (largest fold-to-fold spread, folds range
  0.5281–0.6663) and raises many false alarms (FPR 0.3734).

Per-class results are in `tables/per_class_results`. Two examples, XGBoost
recall on the test set:

| Class | Variant A | Variant B |
|---|---|---|
| dos | 0.8723 | 0.9921 |
| legitimate | 0.8547 | 0.9878 |
| slowite | 0.8280 | 0.9587 |
| bruteforce | 0.7111 | 0.8690 |
| flood ⚠️ | 0.8315 | 0.9000 |
| malformed | 0.6254 | 0.6999 |

⚠️ **`flood` per-class scores are unreliable in both variants.** Variant A's
test set has only 94 unique `flood` feature vectors, and Variant B's has 80,
both below the 100 threshold set in advance.

`malformed` is the hardest attack in both variants. In Task 1 it shared the
most feature vectors with `bruteforce`.

## 3. The headline finding: Variant A scores LOWER than Variant B

The plan expected the leaky published split (A) to look better than the honest
split (B). **The opposite happened: test macro F1 is 0.25–0.26 lower on A for
all three models.** Two checks explain why.

### 3a. Variant A's test set is three different populations

XGBoost and Random Forest, Variant A test rows split by whether the exact
feature vector is in training, and whether that vector carries one label or
several in the full file:

| Test group | Share of test | RF accuracy (balanced / no weights) | XGB accuracy (balanced / no weights) |
|---|---|---|---|
| Seen in train, **one label** | 34.37% | **0.9998 / 1.0000** | **0.9977 / 0.9989** |
| Seen in train, **several labels** | 35.21% | 0.5754 / 0.7898 | 0.5817 / 0.7957 |
| Not seen in train | 30.41% | 0.9846 / 0.9848 | 0.9837 / 0.9859 |

- **Memorisation is real.** A third of the published test set is copies of
  unambiguous training rows, and models get them right almost 100% of the time.
- **But a further third is ambiguous.** These are the bare TCP packets (Step 2
  §2), whose identical vectors carry different labels. They drag Variant A down
  more than memorisation lifts it.
- Variant B keeps only one row per (vector, label), so those heavily repeated
  ambiguous packets shrink to a handful of rows. That, not leakage, is the main
  reason B scores higher.

**So the A − B gap is NOT a measure of how much leakage inflates results.** It
mixes two opposing effects. The cleaner measure of memorisation is the table
above: 34.37% of the published test set is answered almost perfectly because it
was in training.

### 3b. Class weighting matters a lot on Variant A

Same models, retrained **without** class weights (the setting most papers use):

| Variant | Model | Weights | Test macro F1 | Accuracy | FPR |
|---|---|---|---|---|---|
| A | Random Forest | balanced | 0.6094 | 0.8457 | 0.1445 |
| A | Random Forest | none | 0.7760 | 0.9214 | 0.0129 |
| A | XGBoost | balanced | 0.6164 | 0.8470 | 0.1453 |
| A | XGBoost | none | 0.7829 | 0.9234 | 0.0129 |
| B | Random Forest | balanced | 0.8559 | 0.9715 | 0.0066 |
| B | Random Forest | none | 0.8757 | 0.9712 | 0.0050 |
| B | XGBoost | balanced | 0.8673 | 0.9731 | 0.0122 |
| B | XGBoost | none | 0.8802 | 0.9724 | 0.0083 |

- On Variant A, balanced weights push ambiguous packets towards the rare
  classes. That raises rare-class recall but floods them with false alarms:
  `flood` precision falls to 0.026 (`tables/per_class_results`), and the FPR
  rises to 0.145.
- Without weights, Variant A accuracy is 92.1–92.3%, close to the **93.27%
  ceiling** measured in Step 2. That is about as high as any model can go on
  these 20 features.
- On Variant B, weighting makes little difference.
- Weighting is a trade-off, not a free gain: no weights give fewer false alarms
  but lower recall on `flood` and `slowite`.

### What this means for the "97–99%" claim

- On the published split with these 20 features, **no model can exceed 93.27%
  accuracy**, and the measured models reach 92.1–92.3% without weights.
- Variant B accuracies of 95.6–97.3% look closer to the published range. But
  Variant B is about 83% `dos` (*derived*: 90,988 of 108,973 rows), an easy
  class, so its accuracy is not comparable with the literature either. Its
  macro F1 (0.80–0.87) is the honest number.
- Before comparing with any specific paper, check which MQTTset file and
  features it used, and whether it kept `mqtt.msg`: the `slowite` payload
  artefact would give that class away.

## 4. Cost results (for O4)

Measured on the MacBook (official run). Timing numbers vary a little from run
to run.

| Model | Size on disk (A / B) | Latency, one packet at a time (A / B) | Latency, batch, per packet (A / B) | Training time (A / B) |
|---|---|---|---|---|
| Random Forest | 48,573 / 42,049 KB | 3.023 / 2.985 ms | 0.00091 / 0.00122 ms | 1.0 / 0.3 s |
| XGBoost | 1,185 / 1,080 KB | 0.103 / 0.106 ms | 0.00062 / 0.00076 ms | 2.2 / 1.4 s |
| MLP | 124 / 123 KB | 0.163 / 0.164 ms | 0.00021 / 0.00022 ms | 29.6 / 7.0 s |

- **XGBoost gives the best accuracy for its cost.** It is about 40 times smaller
  than Random Forest and about 28–29 times faster one packet at a time
  (*derived*).
- The MLP is the smallest and fastest to run, but the least accurate.

## 5. Feature importance (input to O2)

Figures `importance_RandomForest_variant*.png` and
`importance_XGBoost_variant*.png`.

- For XGBoost on Variant B, the top features are **`mqtt.msgid`**,
  `mqtt.conflag.uname`, `mqtt.conflag.cleansess`, **`tcp.len`**,
  `mqtt.conack.val`, `mqtt.retain`, **`mqtt.kalive`** and `mqtt.hdrflags`.
  Bold = fields the report lists as attacker-mutable.
- **`mqtt.msgid` is non-zero almost only in `dos`.** It is 0 in 100% of
  `legitimate`, `flood`, `slowite` and `bruteforce` rows and in 97.5% of
  `malformed` rows, but in only 28.4% of `dos` rows. MQTT carries a message ID
  only for QoS 1 or 2, so this reflects DoS traffic in this dataset using QoS > 0.
  It is genuine protocol behaviour, but **an attacker can choose QoS 0**, which
  would remove the detector's strongest signal. That is a ready-made O2 attack
  to test.
- `mqtt.msgid` and `mqtt.qos` are not yet in the report's mutable/immutable
  lists. They need classifying for O2.

## 6. Decisions to confirm with Dr. Bryan

1. **Headline framing.** Replace "the A − B gap measures inflation" with the
   three-group breakdown (§3a). The planned framing does not hold for this
   dataset.
2. **Class weighting.** Keep balanced weights as the main setting, as planned,
   and report the no-weights results as a sensitivity check (§3b)?
3. **`mqtt.msg` dropped**, with two reasons: payload memorisation and the
   `slowite` `0.0` artefact. It leaves the O2 constraint set.
4. **`flood`** has fewer than 100 unique test vectors. Report its scores as
   unreliable, as done here.
5. **Bare TCP packets** (37.46% of rows) are the main source of label
   ambiguity. For later phases, consider evaluating on MQTT packets only as an
   additional view. This was not done in Phase 1.

## 7. Still uncertain / not measured

- The sensitivity checks (§3a, §3b) have not been re-run on the Mac yet. For
  Random Forest and XGBoost the main results matched the cloud exactly, so they
  are expected to match, but that is not yet confirmed.
- Why the MLP on Variant A differs between machines (a likely explanation is
  given above, not measured).
- Which MQTTset file and features each cited 97–99% paper used.
- Hyperparameters were not tuned (by design, per the brief). Tuned models could
  score differently.

## Acceptance criteria (brief F8)

| Criterion | Status |
|---|---|
| `python3 src/run_phase1.py` runs end to end | ✅ Mac and cloud |
| Per-class unique counts, all 6 classes | ✅ |
| Precise leakage, % of test rows, per class | ✅ |
| 3 models × 2 variants = 6 result sets | ✅ |
| Every F7 metric for every combination | ✅ |
| Mean ± standard deviation | ✅ (15 folds) |
| Fixed seeds, identical on rerun | ✅ identical on rerun on the same machine; across machines all identical except MLP on Variant A |
| `requirements.txt` with exact versions | ✅ written by each run; commit the Mac one |
| No number not produced by this code | ✅ |
| Runtime under ~30 min | ✅ 10.5 min on the Mac |
