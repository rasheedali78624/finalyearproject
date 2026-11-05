"""
sensitivity_checks.py — how much do the Phase 1 results depend on class weighting?

The main pipeline (run_phase1.py) uses balanced class weights for every model,
as planned. This script retrains Random Forest and XGBoost WITHOUT class weights
(the setting most published MQTT papers use) on both variants, and scores the
held-out test sets once. Settings are otherwise identical.

It is a sensitivity check, not a replacement for the main results.

Run:  python3 src/sensitivity_checks.py     (about 1 minute)
It also splits Variant A's test rows into seen-unambiguous / seen-ambiguous /
unseen, to separate memorisation from label ambiguity.

Writes: results/phase1/tables/sensitivity_class_weighting.csv/.md
        results/phase1/tables/variantA_memorisation_vs_ambiguity.csv/.md
"""
import time

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

import config
import evaluate as ev
from data_loader import encode, load_raw, variant_a, variant_b
from utils import Logger, row_key, save_table

log = Logger("sensitivity_checks")


def build(name, weighted, X, y):
    if name == "RandomForest":
        m = RandomForestClassifier(n_estimators=100, random_state=config.SEED, n_jobs=-1,
                                   class_weight="balanced" if weighted else None)
        return m.fit(X, y)
    m = XGBClassifier(tree_method="hist", random_state=config.SEED, n_jobs=-1)
    return m.fit(X, y, sample_weight=compute_sample_weight("balanced", y) if weighted else None)


def main():
    t0 = time.time()
    X_full, y_full, _ = encode(load_raw(config.FULL_CSV))
    classes = sorted(y_full.unique())
    to_int = {c: i for i, c in enumerate(classes)}
    rows = []
    for v in (variant_a(), variant_b(X_full, y_full)):
        ytr = v["y_train"].map(to_int).to_numpy(); yte = v["y_test"].map(to_int).to_numpy()
        for name in ("RandomForest", "XGBoost"):
            for weighted in (True, False):
                model = build(name, weighted, v["X_train"].to_numpy(), ytr)
                s = ev.scores(yte, model.predict(v["X_test"].to_numpy()), classes)
                row = {"variant": v["name"], "model": name,
                       "class_weights": "balanced" if weighted else "none",
                       "test_macro_f1": round(s["macro_f1"], 4),
                       "test_accuracy": round(s["accuracy"], 4),
                       "test_fpr": round(s["fpr"], 4)}
                row.update({f"recall_{c}": round(s[f"recall_{c}"], 4) for c in classes})
                rows.append(row)
                log(f"  {v['name']} {name:12s} weights={row['class_weights']:8s} "
                    f"macroF1 {row['test_macro_f1']:.4f}  acc {row['test_accuracy']:.4f}  "
                    f"FPR {row['test_fpr']:.4f}")
    df = pd.DataFrame(rows)
    save_table(df, "sensitivity_class_weighting", log)

    # ---- Variant A: separate memorisation from label ambiguity -------------
    # Test rows fall into three groups:
    #   seen_unambiguous : vector also in train, and the vector has ONE label in the full file
    #   seen_ambiguous   : vector also in train, and it carries >1 label in the full file
    #   unseen           : vector not in train
    log("\nVariant A test rows by group (memorisation vs ambiguity):")
    feats = list(X_full.columns)
    full_keys = row_key(X_full, feats)
    n_lab = pd.Series(y_full.to_numpy()).groupby(full_keys.to_numpy()).nunique()
    ambiguous = set(n_lab[n_lab > 1].index)
    va = variant_a()
    ytr = va["y_train"].map(to_int).to_numpy(); yte = va["y_test"].map(to_int).to_numpy()
    te_keys = row_key(va["X_test"], feats)
    seen = te_keys.isin(set(row_key(va["X_train"], feats))).to_numpy()
    amb = te_keys.isin(ambiguous).to_numpy()
    groups = {"seen_unambiguous": seen & ~amb, "seen_ambiguous": seen & amb, "unseen": ~seen}
    grows = []
    for name in ("RandomForest", "XGBoost"):
        for weighted in (True, False):
            yp = build(name, weighted, va["X_train"].to_numpy(), ytr).predict(va["X_test"].to_numpy())
            for g, mask in groups.items():
                s = ev.scores(yte[mask], yp[mask], classes)
                grows.append({"model": name, "class_weights": "balanced" if weighted else "none",
                              "test_group": g, "rows": int(mask.sum()),
                              "share_of_test_pct": round(100 * mask.mean(), 2),
                              "accuracy": round(s["accuracy"], 4),
                              "macro_f1": round(s["macro_f1"], 4)})
    gdf = pd.DataFrame(grows)
    log(gdf.to_string(index=False))
    save_table(gdf, "variantA_memorisation_vs_ambiguity", log)
    log(f"Finished in {time.time() - t0:.0f} s")
    log.save()


if __name__ == "__main__":
    main()
