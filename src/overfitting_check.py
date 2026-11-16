"""
overfitting_check.py — are OUR three models overfitting?

The standard check: score each model twice.
  1. on the rows it was trained on  ("train" score)
  2. on rows it has never seen      ("test" score)
A model that memorised its training data scores much higher on (1) than on (2).
A small gap means it learned patterns that carry over to new data.

Models and settings are exactly those of Phase 1 (models.fit_model, seed 42),
so the test scores here must equal the Phase 1 baseline table. Both variants
are scored: A (published split, with leakage) and B (de-duplicated, leak-free).

Run:  python3 src/overfitting_check.py      (a few minutes)

Writes: results/phase1/tables/overfitting_train_vs_test.csv/.md
        results/phase1/tables/overfitting_per_class_recall.csv/.md
"""
import time

import pandas as pd

import config
import evaluate as ev
from data_loader import encode, load_raw, variant_a, variant_b
from models import MODEL_NAMES, fit_model
from utils import Logger, save_table

log = Logger("overfitting_check")


def main():
    t0 = time.time()
    log("=" * 72)
    log("OVERFITTING CHECK — train score vs test score, Phase 1 models")
    log("=" * 72)
    X_full, y_full, _ = encode(load_raw(config.FULL_CSV))
    classes = sorted(y_full.unique())
    to_int = {c: i for i, c in enumerate(classes)}

    summary, per_class = [], []
    for v in (variant_a(), variant_b(X_full, y_full)):
        Xtr, Xte = v["X_train"].to_numpy(), v["X_test"].to_numpy()
        ytr = v["y_train"].map(to_int).to_numpy()
        yte = v["y_test"].map(to_int).to_numpy()
        log(f"\nVariant {v['name']}: train {len(ytr):,} rows, test {len(yte):,} rows")
        for name in MODEL_NAMES:
            model = fit_model(name, Xtr, ytr)
            tr = ev.scores(ytr, model.predict(Xtr), classes)
            te = ev.scores(yte, model.predict(Xte), classes)
            summary.append({
                "variant": v["name"], "model": name,
                "train_macro_f1": round(tr["macro_f1"], 4),
                "test_macro_f1": round(te["macro_f1"], 4),
                "macro_f1_gap": round(tr["macro_f1"] - te["macro_f1"], 4),
                "train_accuracy": round(tr["accuracy"], 4),
                "test_accuracy": round(te["accuracy"], 4),
                "accuracy_gap": round(tr["accuracy"] - te["accuracy"], 4),
            })
            log(f"  {name:12s} macro F1 train {tr['macro_f1']:.4f}  test {te['macro_f1']:.4f}  "
                f"gap {tr['macro_f1'] - te['macro_f1']:+.4f}")
            for c in classes:
                per_class.append({
                    "variant": v["name"], "model": name, "class": c,
                    "train_rows": tr[f"support_{c}"], "test_rows": te[f"support_{c}"],
                    "train_recall": round(tr[f"recall_{c}"], 4),
                    "test_recall": round(te[f"recall_{c}"], 4),
                    "recall_gap": round(tr[f"recall_{c}"] - te[f"recall_{c}"], 4),
                })

    df = pd.DataFrame(summary)
    save_table(df, "overfitting_train_vs_test", log)
    dfc = pd.DataFrame(per_class)
    save_table(dfc, "overfitting_per_class_recall", log)
    log("\n" + df.to_string(index=False))
    log("\nPer-class recall, Variant B:")
    log(dfc[dfc["variant"] == "B"].drop(columns="variant").to_string(index=False))
    log(f"\nTotal {(time.time() - t0) / 60:.1f} min")
    log.save()


if __name__ == "__main__":
    main()
