# Overfitting check — train score vs test score

**Source:** `src/overfitting_check.py`, run on Rasheed's Mac, 16 Nov 2026
(1.1 min, seed 42). Tables copied from his terminal output. Reproduce:
`python3 src/overfitting_check.py`.

**Why:** the panel's closing comment (26 Aug 2026) asked for evidence on
overfitting in this study's own results, not only in published ones.

**Method:** the three Phase 1 models, unchanged settings, each scored on the
rows it was trained on and on the held-out test rows. A large train − test gap
means memorisation. **Sanity check passed:** all six test scores equal the Mac
Phase 1 baseline table (5 Nov).

## Summary

| variant | model | train_macro_f1 | test_macro_f1 | macro_f1_gap | train_accuracy | test_accuracy | accuracy_gap |
|---|---|---|---|---|---|---|---|
| A | RandomForest | 0.6469 | 0.6094 | 0.0375 | 0.8575 | 0.8457 | 0.0118 |
| A | XGBoost | 0.6320 | 0.6164 | 0.0156 | 0.8539 | 0.8470 | 0.0069 |
| A | MLP | 0.5786 | 0.5837 | -0.0051 | 0.6558 | 0.6551 | 0.0006 |
| B | RandomForest | 0.9041 | 0.8559 | 0.0482 | 0.9810 | 0.9715 | 0.0095 |
| B | XGBoost | 0.8723 | 0.8673 | 0.0050 | 0.9740 | 0.9731 | 0.0008 |
| B | MLP | 0.8086 | 0.8030 | 0.0056 | 0.9556 | 0.9556 | -0.0000 |

## Per-class recall, Variant B

| model | class | train_rows | test_rows | train_recall | test_recall | recall_gap |
|---|---|---|---|---|---|---|
| RandomForest | bruteforce | 3059 | 1313 | 0.9398 | 0.8271 | 0.1127 |
| RandomForest | dos | 63690 | 27298 | 0.9917 | 0.9922 | -0.0005 |
| RandomForest | flood | 186 | 80 | 1.0000 | 0.9000 | 0.1000 |
| RandomForest | legitimate | 4215 | 1808 | 0.9907 | 0.9934 | -0.0026 |
| RandomForest | malformed | 3321 | 1423 | 0.7946 | 0.7070 | 0.0877 |
| RandomForest | slowite | 1805 | 775 | 0.9911 | 0.9290 | 0.0621 |
| XGBoost | bruteforce | 3059 | 1313 | 0.8902 | 0.8690 | 0.0212 |
| XGBoost | dos | 63690 | 27298 | 0.9916 | 0.9921 | -0.0005 |
| XGBoost | flood | 186 | 80 | 1.0000 | 0.9000 | 0.1000 |
| XGBoost | legitimate | 4215 | 1808 | 0.9843 | 0.9878 | -0.0035 |
| XGBoost | malformed | 3321 | 1423 | 0.7115 | 0.6999 | 0.0116 |
| XGBoost | slowite | 1805 | 775 | 0.9518 | 0.9587 | -0.0069 |
| MLP | bruteforce | 3059 | 1313 | 0.7427 | 0.7456 | -0.0029 |
| MLP | dos | 63690 | 27298 | 0.9913 | 0.9919 | -0.0006 |
| MLP | flood | 186 | 80 | 0.8763 | 0.8250 | 0.0513 |
| MLP | legitimate | 4215 | 1808 | 0.9476 | 0.9436 | 0.0040 |
| MLP | malformed | 3321 | 1423 | 0.4715 | 0.4680 | 0.0035 |
| MLP | slowite | 1805 | 775 | 0.9717 | 0.9677 | 0.0040 |

## Reading it

- **XGBoost and the MLP show no meaningful overfitting on Variant B.** Macro F1
  gaps are 0.0050 and 0.0056, smaller than XGBoost's fold-to-fold spread in
  cross-validation (±0.0174, Phase 1).
- **Random Forest overfits mildly** (gap 0.0482), in the smaller attack
  classes: bruteforce 0.11, malformed 0.09, slowite 0.06. Its majority classes
  (dos, legitimate) show no gap. Its test score is still 0.8559.
- **`flood` gap of 0.10 for both tree models is 8 packets out of 80.** Too few
  rows to rely on, consistent with the Phase 1 rule for this class.
- **The MLP's weakness is underfitting, not overfitting:** `malformed` recall
  is 0.47 on its own training rows.
- **Train scores are below 1.0 by construction.** About a third of rows share a
  feature vector with a row of a different label, so no model can fit them all.
- **Variant A shows small gaps too, and that is the point:** with 69.59% of
  test rows also in training, train and test are nearly the same data, so a
  train − test gap cannot reveal the problem. Leakage hides overfitting from
  this check. That is why the de-duplicated Variant B is needed.

## Limit

This shows the models carry over to unseen packet shapes **from the same
captures**. It says nothing about a different network or dataset.
