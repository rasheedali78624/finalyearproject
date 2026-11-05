# Cloud verification run — 5 Nov 2026

Outputs of `src/run_phase1.py` and `src/sensitivity_checks.py`, run in the
Claude Code cloud session (Linux, 4 CPU cores) on Rasheed's uploaded copies of
`mqttdataset_reduced.csv`, `train70_reduced.csv` and `test30_reduced.csv`.
The copies were verified identical to the Mac copies: Task 1 output matched
the Mac log of 5 Nov 12:46 line for line.

Kept here as the evidence behind `docs/phase1/PHASE1_FINDINGS.md`.
The official results are the ones regenerated on the Mac in `results/phase1/`.
Classification numbers should match exactly. Timing and latency will not,
because they depend on the machine.

Library versions used: `requirements_cloud.txt`. Trained models are not
included, because they are large and can be regenerated.
