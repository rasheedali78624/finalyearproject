# Mac confirmation run — O2, O3, O4 (15 Nov 2026)

> **⚠️ SUPERSEDED — DO NOT QUOTE THE O2–O4 NUMBERS IN THIS FOLDER (16 Nov 2026).**
> `src/o2_validity_audit.py` showed that most evasions in this run changed rows
> an attacker cannot reshape (bare TCP rows, broker replies, fixed-length
> packets). The attack rules in `src/constraints.py` were corrected on 16 Nov;
> the corrected run is being confirmed on the Mac and see `../O2_O4_FINDINGS.md`.


Tables printed by `python3 src/run_phase2to4.py` on Rasheed's MacBook Pro
(default settings: budget 120, seed 42), copied from his terminal output.
They are the Mac counterpart of the cloud numbers in `../O2_O4_FINDINGS.md`.

Result of the comparison with the cloud run:

- **O2:** every attack-success figure identical.
- **O3:** identical except Random Forest / report set adaptive re-attack:
  Mac 2.57%, cloud 2.55% (the figure is a mean over five classes, so this is
  about one packet's difference in one class).
- **O4:** clean F1, robustness and model size identical. Latency differs, as
  expected for a different machine (Mac is faster).
