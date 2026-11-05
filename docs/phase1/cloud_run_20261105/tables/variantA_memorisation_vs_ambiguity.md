| model | class_weights | test_group | rows | share_of_test_pct | accuracy | macro_f1 |
|---|---|---|---|---|---|---|
| RandomForest | balanced | seen_unambiguous | 34129 | 34.37 | 0.9998 | 0.999 |
| RandomForest | balanced | seen_ambiguous | 34963 | 35.21 | 0.5754 | 0.4149 |
| RandomForest | balanced | unseen | 30198 | 30.41 | 0.9846 | 0.9091 |
| RandomForest | none | seen_unambiguous | 34129 | 34.37 | 1.0 | 1.0 |
| RandomForest | none | seen_ambiguous | 34963 | 35.21 | 0.7898 | 0.4598 |
| RandomForest | none | unseen | 30198 | 30.41 | 0.9848 | 0.9162 |
| XGBoost | balanced | seen_unambiguous | 34129 | 34.37 | 0.9977 | 0.9353 |
| XGBoost | balanced | seen_ambiguous | 34963 | 35.21 | 0.5817 | 0.4253 |
| XGBoost | balanced | unseen | 30198 | 30.41 | 0.9837 | 0.8514 |
| XGBoost | none | seen_unambiguous | 34129 | 34.37 | 0.9989 | 0.9928 |
| XGBoost | none | seen_ambiguous | 34963 | 35.21 | 0.7957 | 0.4735 |
| XGBoost | none | unseen | 30198 | 30.41 | 0.9859 | 0.9155 |
