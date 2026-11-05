"""
mqtt_only_analysis.py — what changes if we keep only packets that carry an MQTT
layer (mqtt.hdrflags present)?

Why: Step 2 found that 99.89% of label-conflict rows are bare TCP packets with
no MQTT content. Phase 2 attacks perturb MQTT fields, and a bare TCP packet has
none. This script measures the MQTT-only subset so the project can decide which
population O2-O4 should use.

Run:  python3 src/mqtt_only_analysis.py      (about 1 minute)
Writes: results/phase1/tables/mqtt_only_summary.csv/.md
        results/phase1/tables/mqtt_only_models.csv/.md
"""
import time

import numpy as np
import pandas as pd

import config
import evaluate as ev
from data_loader import encode, load_raw, variant_b
from models import fit_model
from utils import Logger, pct, row_key, save_table

log = Logger("mqtt_only_analysis")


def main():
    t0 = time.time()
    raw = load_raw(config.FULL_CSV)
    X, y, _ = encode(raw)
    has_mqtt = (raw["mqtt.hdrflags"] != "0").to_numpy()
    feats = list(X.columns)
    classes = sorted(y.unique())

    log("=" * 72)
    log("MQTT-ONLY SUBSET (rows with an MQTT header)")
    log("=" * 72)
    rows = []
    for name, mask in (("all rows", np.ones(len(X), bool)), ("MQTT-only", has_mqtt)):
        Xs, ys = X[mask].reset_index(drop=True), y[mask].reset_index(drop=True)
        keys = row_key(Xs, feats)
        df = pd.DataFrame({"k": keys, "y": ys})
        counts = df.groupby(["k", "y"]).size()
        floor = int((counts.groupby(level=0).sum() - counts.groupby(level=0).max()).sum())
        n_lab = df.groupby("k")["y"].nunique()
        conf_rows = int(df["k"].isin(set(n_lab[n_lab > 1].index)).sum())
        r = {"population": name, "rows": len(Xs), "unique_vectors": keys.nunique(),
             "rows_in_conflict_pct": pct(conf_rows, len(Xs)),
             "error_floor_pct": pct(floor, len(Xs)),
             "accuracy_ceiling_pct": round(100 - pct(floor, len(Xs)), 2)}
        for c in classes:
            m = ys == c
            r[f"{c}_rows"] = int(m.sum())
            r[f"{c}_unique"] = int(keys[m].nunique())
        rows.append(r)
    summ = pd.DataFrame(rows)
    log(summ.T.to_string(header=False))
    save_table(summ, "mqtt_only_summary", log)

    # Variant-B-style split on the MQTT-only subset, then the three models.
    log("\nVariant B (de-duplicated, grouped split) built on MQTT-only rows:")
    Xm, ym = X[has_mqtt].reset_index(drop=True), y[has_mqtt].reset_index(drop=True)
    vb = variant_b(Xm, ym)
    to_int = {c: i for i, c in enumerate(classes)}
    ytr = vb["y_train"].map(to_int).to_numpy(); yte = vb["y_test"].map(to_int).to_numpy()
    for c in classes:
        log(f"  {c:11s} train {int((vb['y_train'] == c).sum()):6d}  test {int((vb['y_test'] == c).sum()):6d}")
    res = []
    for m in ("RandomForest", "XGBoost", "MLP"):
        model = fit_model(m, vb["X_train"].to_numpy(), ytr)
        s = ev.scores(yte, model.predict(vb["X_test"].to_numpy()), classes)
        row = {"model": m, "test_macro_f1": round(s["macro_f1"], 4),
               "test_accuracy": round(s["accuracy"], 4), "test_fpr": round(s["fpr"], 4)}
        row.update({f"recall_{c}": round(s[f"recall_{c}"], 4) for c in classes})
        res.append(row)
        log(f"  {m:12s} macro F1 {row['test_macro_f1']:.4f}  accuracy {row['test_accuracy']:.4f}  "
            f"FPR {row['test_fpr']:.4f}")
    res_df = pd.DataFrame(res)
    log(res_df.to_string(index=False))
    save_table(res_df, "mqtt_only_models", log)
    log(f"Finished in {time.time() - t0:.0f} s")
    log.save()


if __name__ == "__main__":
    main()
