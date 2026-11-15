"""
run_phase2to4.py — run Objectives O2, O3 and O4 end to end.

    python3 src/run_phase2to4.py                  # default budget/sample sizes
    python3 src/run_phase2to4.py --quick          # smaller, for a fast check

Order:
  O2  phase2_attacks   constraint-aware evasion -> adversarial samples + ASR table
  O3  phase3_defence   adversarial training + adaptive re-attack
  O4  phase4_tradeoff  robustness vs accuracy vs cost table and figure

Phase 1 (O1) is produced by run_phase1.py and is a prerequisite only in that it
established the baseline; O2-O4 here retrain the same models internally, so this
script is self-contained. Fixed seed 42 throughout.
"""
import argparse
import subprocess
import sys

import config


def run(mod, extra):
    cmd = [sys.executable, str(config.PROJECT_ROOT / "src" / mod)] + extra
    print(f"\n>>> {' '.join(cmd)}\n", flush=True)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(f"{mod} failed with exit {r.returncode}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--harden", action="store_true", default=True)
    args = ap.parse_args()
    budget = ["--budget", "60"] if args.quick else ["--budget", "120"]
    per = ["--per-class", "300"] if args.quick else ["--per-class", "1200"]

    run("phase2_attacks.py", budget + per)
    run("phase3_defence.py", budget + per + (["--harden"] if args.harden else []))
    run("phase4_tradeoff.py", budget + (["--per-class", "300"] if args.quick else ["--per-class", "800"]))
    print("\nO2-O4 complete. Tables in results/phase2|phase3 and results/phase1/tables; "
          "figure results/phase1/figures/o4_tradeoff.png")


if __name__ == "__main__":
    main()
