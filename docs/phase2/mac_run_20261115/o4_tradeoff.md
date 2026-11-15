| model | variant | clean_macro_f1 | robustness_pct | latency_ms_per_packet | model_size_kb |
|---|---|---|---|---|---|
| RandomForest | baseline | 0.8559 | 95.08 | 3.108 | 42049.2 |
| RandomForest | defended | 0.8572 | 99.98 | 3.283 | 42263.5 |
| XGBoost | baseline | 0.8673 | 70.36 | 0.103 | 1080.1 |
| XGBoost | defended | 0.8705 | 99.85 | 0.104 | 1085.8 |
| MLP | baseline | 0.8030 | 24.29 | 0.163 | 123.4 |
| MLP | defended | 0.8151 | 92.32 | 0.166 | 123.1 |
