"""
dedup_analysis.py — Phase 1, Task 1: duplication and leakage analysis.

Run from the repository folder:
    python3 src/dedup_analysis.py

What it answers (each becomes a table in results/phase1/tables/):
  1. constant_columns    Which columns never change? (re-checks the brief's 12)
  2. split_check         Do train70 + test30 add up to the full file, per class?
  3. duplication_per_class
                         For each class: total rows, UNIQUE rows, duplicate %.
                         Classes with < MIN_UNIQUE_WARN unique rows are flagged.
  4. label_conflicts     Identical feature vectors that carry DIFFERENT labels.
                         No model can get these all right, so they cap accuracy.
  5. leakage_per_class   How many TEST rows have a feature vector that also
                         appears in TRAIN (full files, no sampling).
  6. text_columns        The text (object) columns: distinct values + examples.

Key definition used everywhere below:
  "feature vector" = all columns EXCEPT the label 'target'.
  Two rows are duplicates if their feature vectors are character-for-character
  identical. We compare the raw text exactly as written in the CSV, so there is
  no rounding or type-guessing involved.

This script only READS the dataset. It never modifies the raw files.
"""
import sys
import time
from datetime import datetime

import pandas as pd

import config

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
_log_lines = []


def log(msg=""):
    """Print a line AND keep it, so the whole console output is saved to a log file."""
    print(msg)
    _log_lines.append(str(msg))


def to_markdown(df):
    """Turn a DataFrame into a Markdown table (no extra library needed)."""
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.values) + " |")
    return "\n".join(lines) + "\n"


def save_table(df, name):
    """Save a table as both CSV (for code) and Markdown (for the report)."""
    csv_path = config.TABLES_DIR / f"{name}.csv"
    md_path = config.TABLES_DIR / f"{name}.md"
    df.to_csv(csv_path, index=False)
    md_path.write_text(to_markdown(df))
    log(f"  saved -> {csv_path.relative_to(config.PROJECT_ROOT)}  (+ .md)")


def load_as_text(path):
    """
    Read a CSV with EVERY value kept as the exact text in the file.
    dtype=str            -> no number parsing, so '0x00000010' stays as written
    keep_default_na=False -> an empty cell stays '' instead of becoming NaN
    """
    if not path.exists():
        log(f"ERROR: file not found: {path}")
        log("Check that MQTT_DATA_DIR / config.DATA_DIR points at the FINAL_CSV folder.")
        sys.exit(1)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def feature_key(df, feature_cols):
    """
    Build one string per row by joining all feature values with a separator
    character that never appears in the data. Two rows get the same key
    if and only if every feature value is identical. This is exact — no hashing.
    """
    sep = "\x1f"  # ASCII 'unit separator'
    key = df[feature_cols[0]].astype(str)
    for c in feature_cols[1:]:
        key = key + sep + df[c].astype(str)
    return key


def pct(part, whole):
    return round(100.0 * part / whole, 2) if whole else float("nan")


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------
def main():
    t0 = time.time()
    config.ensure_output_dirs()
    label = config.LABEL_COL

    log("=" * 72)
    log("PHASE 1 / TASK 1 — DUPLICATION AND LEAKAGE ANALYSIS")
    log(f"Run started : {datetime.now().isoformat(timespec='seconds')}")
    log(f"Python      : {sys.version.split()[0]}   pandas: {pd.__version__}")
    log(f"Data folder : {config.DATA_DIR}")
    log("=" * 72)

    # ---- Load ------------------------------------------------------------
    log("\nLoading files (as exact text)...")
    full = load_as_text(config.FULL_CSV)
    train = load_as_text(config.TRAIN_CSV)
    test = load_as_text(config.TEST_CSV)
    for name, df in (("full", full), ("train70", train), ("test30", test)):
        log(f"  {name:8s}: {len(df):>9,} rows x {df.shape[1]} columns")

    if label not in full.columns:
        log(f"ERROR: label column '{label}' not found. Columns are: {list(full.columns)}")
        sys.exit(1)
    if list(train.columns) != list(full.columns) or list(test.columns) != list(full.columns):
        log("WARNING: column names/order differ between the three files.")

    feature_cols = [c for c in full.columns if c != label]
    log(f"  feature columns: {len(feature_cols)}   label column: '{label}'")

    # ---- 1. Constant columns --------------------------------------------
    log("\n[1] Constant (zero-variance) columns in the full file")
    n_distinct = full[feature_cols].nunique(dropna=False)
    constant = n_distinct[n_distinct == 1].index.tolist()
    const_df = pd.DataFrame(
        {
            "column": constant,
            "only_value": [repr(full[c].iloc[0]) for c in constant],
            "in_brief_list": [c in config.BRIEF_CONSTANT_COLS for c in constant],
        }
    )
    log(f"  found {len(constant)} constant columns "
        f"-> {len(feature_cols) - len(constant)} usable features")
    missing_from_data = sorted(set(config.BRIEF_CONSTANT_COLS) - set(constant))
    extra_in_data = sorted(set(constant) - set(config.BRIEF_CONSTANT_COLS))
    log(f"  matches brief's list of 12: {not missing_from_data and not extra_in_data}")
    if missing_from_data:
        log(f"  in brief but NOT constant here: {missing_from_data}")
    if extra_in_data:
        log(f"  constant here but NOT in brief: {extra_in_data}")
    save_table(const_df, "constant_columns")

    # ---- 2. Split check --------------------------------------------------
    log("\n[2] Do train70 + test30 add up to the full file?")
    classes = sorted(full[label].unique())
    split_rows = []
    for cls in classes:
        n_full = int((full[label] == cls).sum())
        n_tr = int((train[label] == cls).sum())
        n_te = int((test[label] == cls).sum())
        split_rows.append({
            "class": cls, "full_rows": n_full, "train70_rows": n_tr, "test30_rows": n_te,
            "train_plus_test": n_tr + n_te, "difference_vs_full": n_tr + n_te - n_full,
            "test_share_pct": pct(n_te, n_tr + n_te),
        })
    split_df = pd.DataFrame(split_rows)
    tot = {"class": "TOTAL"}
    for c in ["full_rows", "train70_rows", "test30_rows", "train_plus_test", "difference_vs_full"]:
        tot[c] = int(split_df[c].sum())
    tot["test_share_pct"] = pct(tot["test30_rows"], tot["train_plus_test"])
    split_df = pd.concat([split_df, pd.DataFrame([tot])], ignore_index=True)
    log(split_df.to_string(index=False))
    extra_labels = (set(train[label]) | set(test[label])) - set(classes)
    if extra_labels:
        log(f"  WARNING: labels in split files but not in full file: {extra_labels}")
    save_table(split_df, "split_check")

    # ---- 3. Duplication per class ---------------------------------------
    log("\n[3] Duplication per class (full file; feature vector = all columns except label)")
    full["_key"] = feature_key(full, feature_cols)
    exact_row_dups = int(full.duplicated(subset=feature_cols + [label]).sum())
    feature_dups = int(full["_key"].duplicated().sum())
    log(f"  exact duplicate rows (features + label): {exact_row_dups:,} "
        f"of {len(full):,} = {pct(exact_row_dups, len(full))}%")
    log(f"  duplicate feature vectors (label ignored): {feature_dups:,} "
        f"of {len(full):,} = {pct(feature_dups, len(full))}%")
    log(f"  unique feature vectors in whole file: {full['_key'].nunique():,}")

    dup_rows = []
    for cls in classes:
        keys = full.loc[full[label] == cls, "_key"]
        n, u = len(keys), keys.nunique()
        dup_rows.append({
            "class": cls, "total_rows": n, "unique_rows": u,
            "duplicate_rows": n - u, "duplicate_pct": pct(n - u, n),
            "flag": f"TOO FEW UNIQUE (<{config.MIN_UNIQUE_WARN})" if u < config.MIN_UNIQUE_WARN else "",
        })
    dup_df = pd.DataFrame(dup_rows)
    log(dup_df.to_string(index=False))
    for r in dup_rows:
        if r["flag"]:
            log(f"  !!! WARNING: class '{r['class']}' has only {r['unique_rows']} unique rows. "
                "Any per-class score for it will be unreliable.")
    save_table(dup_df, "duplication_per_class")

    # ---- 4. Label conflicts ---------------------------------------------
    log("\n[4] Label conflicts: identical feature vectors with different labels")
    labels_per_key = full.groupby("_key")[label].nunique()
    conflict_keys = set(labels_per_key[labels_per_key > 1].index)
    in_conflict = full["_key"].isin(conflict_keys)
    log(f"  feature vectors with >1 label: {len(conflict_keys):,}")
    log(f"  rows involved: {int(in_conflict.sum()):,} of {len(full):,} = "
        f"{pct(int(in_conflict.sum()), len(full))}%")
    conf_rows = []
    for cls in classes:
        m = full[label] == cls
        k = int((m & in_conflict).sum())
        conf_rows.append({"class": cls, "total_rows": int(m.sum()),
                          "rows_with_conflicting_label": k,
                          "conflict_pct": pct(k, int(m.sum()))})
    conf_df = pd.DataFrame(conf_rows)
    log(conf_df.to_string(index=False))
    # Which label pairs collide?
    if conflict_keys:
        pairs = (full.loc[in_conflict].groupby("_key")[label]
                 .apply(lambda s: " + ".join(sorted(s.unique()))).value_counts())
        log("  label combinations among conflicting vectors (count of vectors):")
        for combo, cnt in pairs.items():
            log(f"    {combo}: {cnt:,}")
    save_table(conf_df, "label_conflicts")

    # ---- 5. Train/test leakage (full files) -----------------------------
    log("\n[5] Train/test leakage: test rows whose feature vector appears anywhere in train")
    train_keys = set(feature_key(train, feature_cols))
    test = test.copy()
    test["_key"] = feature_key(test, feature_cols)
    test["_leaked"] = test["_key"].isin(train_keys)
    # Of the leaked rows: does train hold the same vector with the SAME label?
    train_pairs = set(zip(feature_key(train, feature_cols), train[label]))
    test["_leaked_same_label"] = [
        (k, y) in train_pairs for k, y in zip(test["_key"], test[label])
    ]
    leak_rows = []
    for cls in sorted(test[label].unique()):
        m = test[label] == cls
        n = int(m.sum())
        lk = int((m & test["_leaked"]).sum())
        same = int((m & test["_leaked_same_label"]).sum())
        leak_rows.append({"class": cls, "test_rows": n, "leaked_rows": lk,
                          "leaked_pct": pct(lk, n),
                          "leaked_with_same_label_in_train": same})
    n_all, lk_all = len(test), int(test["_leaked"].sum())
    leak_rows.append({"class": "TOTAL", "test_rows": n_all, "leaked_rows": lk_all,
                      "leaked_pct": pct(lk_all, n_all),
                      "leaked_with_same_label_in_train": int(test["_leaked_same_label"].sum())})
    leak_df = pd.DataFrame(leak_rows)
    log(leak_df.to_string(index=False))
    log("  (This uses ALL rows of both files and compares whole rows, replacing the "
        "earlier sampled 22.6% estimate.)")
    save_table(leak_df, "leakage_per_class")

    # ---- 6. Text column inventory ---------------------------------------
    log("\n[6] Text (object) columns — needed to plan encoding")
    # Re-read the full file with normal type detection to see which columns
    # pandas cannot treat as numbers.
    typed = pd.read_csv(config.FULL_CSV, low_memory=False)
    # "not numeric" works on every pandas version (older ones call text 'object',
    # pandas 3 calls it 'str').
    obj_cols = [c for c in typed.columns
                if not pd.api.types.is_numeric_dtype(typed[c]) and c != label]
    log(f"  dtype counts: {typed.dtypes.astype(str).value_counts().to_dict()}")
    log(f"  text feature columns (label excluded): {len(obj_cols)}")
    txt_rows = []
    for c in obj_cols:
        vc = typed[c].astype(str).value_counts()
        examples = list(vc.index[:3])
        txt_rows.append({
            "column": c, "distinct_values": int(typed[c].nunique(dropna=False)),
            "is_constant": c in constant,
            "top3_examples": " ; ".join(repr(e if len(e) <= 40 else e[:40] + "...") for e in examples),
        })
    txt_df = pd.DataFrame(txt_rows)
    log(txt_df.to_string(index=False))
    save_table(txt_df, "text_columns")

    # ---- Save log --------------------------------------------------------
    log(f"\nFinished in {time.time() - t0:.1f} s")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = config.LOGS_DIR / f"task1_dedup_{stamp}.txt"
    log_path.write_text("\n".join(_log_lines) + "\n")
    print(f"Full log saved -> {log_path.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
