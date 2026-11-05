"""
utils.py — small helpers shared by the Phase 1 scripts:
logging to screen + file, saving tables as CSV and Markdown, exact row keys.
"""
from datetime import datetime

import pandas as pd

import config


class Logger:
    """Print a line and remember it, so the whole run can be saved as a log file."""

    def __init__(self, name):
        self.name = name
        self.lines = []

    def __call__(self, msg=""):
        print(msg, flush=True)
        self.lines.append(str(msg))

    def save(self):
        config.ensure_output_dirs()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = config.LOGS_DIR / f"{self.name}_{stamp}.txt"
        path.write_text("\n".join(self.lines) + "\n")
        print(f"Full log saved -> {path.relative_to(config.PROJECT_ROOT)}")
        return path


def to_markdown(df):
    """DataFrame -> Markdown table text (no extra library needed)."""
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.values) + " |")
    return "\n".join(lines) + "\n"


def save_table(df, name, log=print):
    """Save one table as CSV (for code) and Markdown (for the report)."""
    config.ensure_output_dirs()
    df.to_csv(config.TABLES_DIR / f"{name}.csv", index=False)
    (config.TABLES_DIR / f"{name}.md").write_text(to_markdown(df))
    log(f"  saved -> results/phase1/tables/{name}.csv (+ .md)")


def row_key(df, cols):
    """
    One exact string per row made by joining the values of `cols`.
    Two rows get the same key if and only if all those values are identical.
    """
    sep = "\x1f"
    key = df[cols[0]].astype(str)
    for c in cols[1:]:
        key = key + sep + df[c].astype(str)
    return key


def pct(part, whole):
    return round(100.0 * part / whole, 2) if whole else float("nan")
