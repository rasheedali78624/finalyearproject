"""
feature_space_analysis.py — Phase 1, Step 2: re-measure on the features the
models will actually use (after encoding, dropping constants and mqtt.msg).

Run:  python3 src/feature_space_analysis.py

Tables written to results/phase1/tables/:
  encoding_report            each kept column: rule used, distinct raw/encoded values
  no_mqtt_rows               per class: rows with no MQTT header (mqtt.hdrflags = '0')
  fs_duplication_per_class   duplication in the final feature space
  fs_label_conflicts         label conflicts + error floor in the final feature space
  fs_leakage_per_class       Variant A test rows whose vector appears in train
  variant_b_summary          Variant B rows per class, and leakage check (must be 0)
"""
import sys
import time

import pandas as pd

import config
from data_loader import encode, feature_columns, load_raw, variant_b
from utils import Logger, pct, row_key, save_table

log = Logger("step2_feature_space")


def duplication(keys, y, classes):
    rows = []
    for c in classes:
        k = keys[y == c]
        n, u = len(k), k.nunique()
        rows.append({"class": c, "total_rows": n, "unique_rows": u,
                     "duplicate_pct": pct(n - u, n),
                     "flag": f"TOO FEW UNIQUE (<{config.MIN_UNIQUE_WARN})"
                     if u < config.MIN_UNIQUE_WARN else ""})
    return pd.DataFrame(rows)


def conflicts(keys, y, classes):
    df = pd.DataFrame({"k": keys.to_numpy(), "y": y.to_numpy()})
    n_lab = df.groupby("k")["y"].nunique()
    conflict_keys = set(n_lab[n_lab > 1].index)
    in_conf = df["k"].isin(conflict_keys)
    counts = df.groupby(["k", "y"]).size()
    floor = int((counts.groupby(level=0).sum() - counts.groupby(level=0).max()).sum())
    rows = []
    for c in classes:
        m = df["y"] == c
        rows.append({"class": c, "rows": int(m.sum()),
                     "rows_in_conflict": int((m & in_conf).sum()),
                     "conflict_pct": pct(int((m & in_conf).sum()), int(m.sum()))})
    return pd.DataFrame(rows), len(conflict_keys), int(in_conf.sum()), floor, in_conf


def main():
    t0 = time.time()
    config.ensure_output_dirs()
    log("=" * 72)
    log("PHASE 1 / STEP 2 — FEATURE-SPACE ANALYSIS")
    log(f"Python {sys.version.split()[0]}  pandas {pd.__version__}")
    log(f"Data folder: {config.DATA_DIR}")
    log("=" * 72)

    raw = load_raw(config.FULL_CSV)
    X, y, rules = encode(raw)
    feats = list(X.columns)
    classes = sorted(y.unique())
    log(f"\nFull file: {len(raw):,} rows. Features kept: {len(feats)} "
        f"(33 - {len(config.BRIEF_CONSTANT_COLS)} constant - {len(config.DROPPED_COLS)} dropped)")
    log(f"Dropped on purpose: {config.DROPPED_COLS}")

    # ---- Encoding report -------------------------------------------------
    log("\n[1] Encoding applied to each kept column")
    enc = pd.DataFrame([{
        "column": c, "rule": rules[c],
        "distinct_raw": raw[c].nunique(), "distinct_encoded": X[c].nunique(),
        "field_group": "TCP" if c.startswith("tcp.") else "MQTT",
    } for c in feats])
    log(enc.to_string(index=False))
    merged = enc[enc.distinct_raw != enc.distinct_encoded]
    if len(merged):
        log("  NOTE: these columns have fewer encoded than raw values "
            "(different spellings of the same number):")
        log(merged[["column", "distinct_raw", "distinct_encoded"]].to_string(index=False))
    save_table(enc, "encoding_report", log)

    # ---- Hypothesis: conflicts are packets without an MQTT layer -----------
    log("\n[2] Rows with no MQTT header (mqtt.hdrflags == '0' in the raw file)")
    no_mqtt = (raw["mqtt.hdrflags"] == "0").reset_index(drop=True)
    keys = row_key(X, feats)
    conf_df, n_conf_keys, n_conf_rows, floor, in_conf = conflicts(keys, y, classes)
    nm_rows = []
    for c in classes:
        m = y == c
        nm_rows.append({"class": c, "rows": int(m.sum()),
                        "no_mqtt_rows": int((m & no_mqtt).sum()),
                        "no_mqtt_pct": pct(int((m & no_mqtt).sum()), int(m.sum()))})
    nm_df = pd.DataFrame(nm_rows)
    log(nm_df.to_string(index=False))
    log(f"  all rows with no MQTT header: {int(no_mqtt.sum()):,} of {len(raw):,} "
        f"= {pct(int(no_mqtt.sum()), len(raw))}%")
    a = int((in_conf.to_numpy() & no_mqtt.to_numpy()).sum())
    log(f"  of the {n_conf_rows:,} rows in a label conflict, {a:,} "
        f"({pct(a, n_conf_rows)}%) have no MQTT header")
    b = int((~in_conf.to_numpy() & no_mqtt.to_numpy()).sum())
    log(f"  of the {len(raw) - n_conf_rows:,} rows NOT in a conflict, {b:,} "
        f"({pct(b, len(raw) - n_conf_rows)}%) have no MQTT header")
    save_table(nm_df, "no_mqtt_rows", log)

    # ---- Duplication / conflicts in feature space ------------------------
    log(f"\n[3] Duplication in the final {len(feats)}-feature space (full file)")
    dup_df = duplication(keys, y, classes)
    log(dup_df.to_string(index=False))
    log(f"  unique feature vectors: {keys.nunique():,} of {len(keys):,}")
    save_table(dup_df, "fs_duplication_per_class", log)

    log(f"\n[4] Label conflicts and error floor in the final feature space")
    log(f"  vectors with >1 label: {n_conf_keys:,}; rows involved: {n_conf_rows:,} "
        f"= {pct(n_conf_rows, len(keys))}%")
    log(f"  UNAVOIDABLE errors: {floor:,} = {pct(floor, len(keys))}%  ->  "
        f"best possible accuracy {round(100 - pct(floor, len(keys)), 2)}%")
    log(conf_df.to_string(index=False))
    conf_df["error_floor_rows_all_classes"] = floor
    save_table(conf_df, "fs_label_conflicts", log)

    # ---- Leakage, Variant A, feature space -------------------------------
    log("\n[5] Variant A leakage in the final feature space")
    tr_raw, te_raw = load_raw(config.TRAIN_CSV), load_raw(config.TEST_CSV)
    Xtr, ytr, _ = encode(tr_raw)
    Xte, yte, _ = encode(te_raw)
    tr_keys = set(row_key(Xtr, feats))
    leaked = row_key(Xte, feats).isin(tr_keys)
    lk = []
    for c in classes:
        m = yte == c
        lk.append({"class": c, "test_rows": int(m.sum()), "leaked_rows": int((m & leaked).sum()),
                   "leaked_pct": pct(int((m & leaked).sum()), int(m.sum()))})
    lk.append({"class": "TOTAL", "test_rows": len(yte), "leaked_rows": int(leaked.sum()),
               "leaked_pct": pct(int(leaked.sum()), len(yte))})
    lk_df = pd.DataFrame(lk)
    log(lk_df.to_string(index=False))
    save_table(lk_df, "fs_leakage_per_class", log)

    # ---- Variant B --------------------------------------------------------
    log("\n[6] Variant B (de-duplicated, grouped + stratified split)")
    vb = variant_b(X, y)
    vb_keys_tr = set(row_key(vb["X_train"], feats))
    vb_leak = int(row_key(vb["X_test"], feats).isin(vb_keys_tr).sum())
    rows = []
    for c in classes:
        ntr = int((vb["y_train"] == c).sum()); nte = int((vb["y_test"] == c).sum())
        rows.append({"class": c, "train_rows": ntr, "test_rows": nte,
                     "test_share_pct": pct(nte, ntr + nte),
                     "flag": f"FEW TEST ROWS (<{config.MIN_UNIQUE_WARN})"
                     if nte < config.MIN_UNIQUE_WARN else ""})
    ntr, nte = len(vb["y_train"]), len(vb["y_test"])
    rows.append({"class": "TOTAL", "train_rows": ntr, "test_rows": nte,
                 "test_share_pct": pct(nte, ntr + nte), "flag": ""})
    vb_df = pd.DataFrame(rows)
    log(vb_df.to_string(index=False))
    log(f"  test rows whose feature vector appears in Variant B train: {vb_leak} (must be 0)")
    save_table(vb_df, "variant_b_summary", log)

    log(f"\nFinished in {time.time() - t0:.1f} s")
    log.save()


if __name__ == "__main__":
    main()
