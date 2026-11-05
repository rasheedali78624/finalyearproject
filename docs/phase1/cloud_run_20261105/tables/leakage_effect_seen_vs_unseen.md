| variant | model | test_subset | rows | share_of_test_pct | macro_f1 | accuracy |
|---|---|---|---|---|---|---|
| A | RandomForest | seen_in_train | 69092 | 69.59 | 0.5455 | 0.785 |
| A | RandomForest | unseen | 30198 | 30.41 | 0.9091 | 0.9846 |
| A | XGBoost | seen_in_train | 69092 | 69.59 | 0.5533 | 0.7872 |
| A | XGBoost | unseen | 30198 | 30.41 | 0.8514 | 0.9837 |
| A | MLP | seen_in_train | 69092 | 69.59 | 0.3461 | 0.482 |
| A | MLP | unseen | 30198 | 30.41 | 0.853 | 0.9754 |
| B | RandomForest | unseen | 32697 | 100.0 | 0.8559 | 0.9715 |
| B | XGBoost | unseen | 32697 | 100.0 | 0.8673 | 0.9731 |
| B | MLP | unseen | 32697 | 100.0 | 0.803 | 0.9556 |
