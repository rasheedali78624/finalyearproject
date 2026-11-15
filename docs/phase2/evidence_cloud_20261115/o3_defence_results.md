| model | constraint_set | defence | clean_f1_undefended | clean_f1_defended | clean_f1_change | static_asr_old_samples | adaptive_reattack_asr | adv_samples_trained |
|---|---|---|---|---|---|---|---|---|
| RandomForest | report | adversarial_training | 0.8559 | 0.8564 | 0.0004 | 1.6 | 2.55 | 124 |
| RandomForest | report | adv_training+feature_hardening | 0.8559 | 0.8536 | -0.0023 | 1.6 | 9.42 | 124 |
| RandomForest | extended | adversarial_training | 0.8559 | 0.8572 | 0.0012 | 0.0 | 0.02 | 129 |
| RandomForest | extended | adv_training+feature_hardening | 0.8559 | 0.8541 | -0.0018 | 0.0 | 6.08 | 129 |
| XGBoost | report | adversarial_training | 0.8673 | 0.8667 | -0.0006 | 0.0 | 0.18 | 721 |
| XGBoost | report | adv_training+feature_hardening | 0.8673 | 0.862 | -0.0053 | 0.0 | 5.05 | 721 |
| XGBoost | extended | adversarial_training | 0.8673 | 0.8705 | 0.0031 | 0.14 | 0.12 | 724 |
| XGBoost | extended | adv_training+feature_hardening | 0.8673 | 0.8653 | -0.0021 | 0.0 | 5.23 | 724 |
| MLP | report | adversarial_training | 0.803 | 0.8069 | 0.0039 | 3.92 | 6.53 | 1964 |
| MLP | report | adv_training+feature_hardening | 0.803 | 0.7966 | -0.0064 | 3.92 | 20.6 | 1964 |
| MLP | extended | adversarial_training | 0.803 | 0.8151 | 0.0121 | 4.05 | 7.88 | 1953 |
| MLP | extended | adv_training+feature_hardening | 0.803 | 0.8157 | 0.0127 | 3.79 | 3.37 | 1953 |
