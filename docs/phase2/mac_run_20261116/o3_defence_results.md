| model | constraint_set | defence | clean_f1_undefended | clean_f1_defended | clean_f1_change | static_asr_old_samples | adaptive_reattack_asr | adaptive_end_to_end_miss | adv_samples_trained |
|---|---|---|---|---|---|---|---|---|---|
| RandomForest | report | adversarial_training | 0.8559 | 0.8568 | 0.0008 | 2.03 | 6.79 | 6.79 | 148 |
| RandomForest | report | adv_training+feature_hardening | 0.8559 | 0.8540 | -0.0019 | 2.03 | 7.56 | 7.56 | 148 |
| RandomForest | extended | adversarial_training | 0.8559 | 0.8571 | 0.0012 | 1.33 | 6.76 | 6.76 | 149 |
| RandomForest | extended | adv_training+feature_hardening | 0.8559 | 0.8544 | -0.0015 | 1.33 | 7.53 | 7.53 | 149 |
| XGBoost | report | adversarial_training | 0.8673 | 0.8688 | 0.0015 | 0.00 | 0.39 | 0.49 | 233 |
| XGBoost | report | adv_training+feature_hardening | 0.8673 | 0.8630 | -0.0044 | 0.00 | 0.04 | 0.14 | 233 |
| XGBoost | extended | adversarial_training | 0.8673 | 0.8688 | 0.0015 | 0.00 | 0.42 | 0.52 | 233 |
| XGBoost | extended | adv_training+feature_hardening | 0.8673 | 0.8630 | -0.0044 | 0.00 | 0.04 | 0.14 | 233 |
| MLP | report | adversarial_training | 0.8030 | 0.8032 | 0.0002 | 9.25 | 6.64 | 6.84 | 1069 |
| MLP | report | adv_training+feature_hardening | 0.8030 | 0.8153 | 0.0123 | 9.25 | 26.57 | 26.77 | 1069 |
| MLP | extended | adversarial_training | 0.8030 | 0.8011 | -0.0019 | 7.82 | 9.86 | 10.01 | 1086 |
| MLP | extended | adv_training+feature_hardening | 0.8030 | 0.7896 | -0.0134 | 0.00 | 7.55 | 7.71 | 1086 |
