| model | variant | clean_macro_f1 | robustness_pct | latency_ms_per_packet | model_size_kb |
|---|---|---|---|---|---|
| RandomForest | baseline | 0.8559 | 89.06 | 3.087 | 42049.2 |
| RandomForest | defended | 0.8571 | 93.24 | 3.246 | 42151.4 |
| XGBoost | baseline | 0.8673 | 83.52 | 0.105 | 1080.1 |
| XGBoost | defended | 0.8688 | 99.58 | 0.106 | 1099.7 |
| MLP | baseline | 0.8030 | 17.60 | 0.161 | 123.4 |
| MLP | defended | 0.8011 | 90.14 | 0.162 | 123.0 |
