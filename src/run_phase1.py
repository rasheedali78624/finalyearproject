"""
run_phase1.py — runs ALL of Phase 1 end to end.

    python3 src/run_phase1.py                 # full run (brief settings)
    python3 src/run_phase1.py --repeats 1     # faster: 5-fold CV once instead of 3 times
    python3 src/run_phase1.py --skip-analysis # skip Task 1 / Step 2 tables (already made)

Order:
  1. Task 1  duplication + leakage on the raw files     (dedup_analysis.py)
  2. Step 2  re-measure on the 20 model features         (feature_space_analysis.py)
  3. Build Variant A (published split) and Variant B (de-duplicated, grouped split)
  4. For each variant x model:
       - cross-validation on the TRAINING set only -> mean +- std
         A: RepeatedStratifiedKFold(5 x repeats)
         B: StratifiedGroupKFold(5), repeated with seeds 42, 43, ... (groups keep
            identical feature vectors in one fold, so CV is leak-free too)
       - fit on the full training set, evaluate ONCE on the held-out test set
       - latency, model size, confusion matrix, feature importance
  5. Tables, figures, an auto-generated results summary, and requirements.txt
"""
import argparse
import platform
import sys
import time
from importlib import metadata

import numpy as np
import pandas as pd
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedGroupKFold

import config
import evaluate as ev
from data_loader import encode, load_raw, variant_a, variant_b
from models import MLP_SUPPORTS_WEIGHTS, MODEL_NAMES, feature_importance, fit_model
from utils import Logger, row_key, save_table, to_markdown

log = Logger("phase1_run")
PACKAGES = ["numpy", "pandas", "scikit-learn", "xgboost", "matplotlib", "joblib"]


def versions():
    out = {}
    for p in PACKAGES:
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            out[p] = "not installed"
    return out


def cv_splits(variant, y_int, repeats):
    X = variant["X_train"]
    if variant["groups_train"] is None:
        cv = RepeatedStratifiedKFold(n_splits=config.CV_SPLITS, n_repeats=repeats,
                                     random_state=config.SEED)
        yield from cv.split(X, y_int)
    else:
        for r in range(repeats):
            cv = StratifiedGroupKFold(n_splits=config.CV_SPLITS, shuffle=True,
                                      random_state=config.SEED + r)
            yield from cv.split(X, y_int, variant["groups_train"])


def fmt(mean, std):
    return f"{mean:.4f} ± {std:.4f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=config.CV_REPEATS)
    ap.add_argument("--models", default=",".join(MODEL_NAMES))
    ap.add_argument("--skip-analysis", action="store_true")
    args = ap.parse_args()
    models = [m.strip() for m in args.models.split(",")]
    np.random.seed(config.SEED)
    t_start = time.time()
    config.ensure_output_dirs()

    log("=" * 72)
    log("PHASE 1 — FULL RUN")
    log(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Machine: {platform.platform()}  CPU cores: {__import__('os').cpu_count()}")
    log(f"Python {sys.version.split()[0]}  " + "  ".join(f"{k} {v}" for k, v in versions().items()))
    log(f"Seed {config.SEED}; CV {config.CV_SPLITS} folds x {args.repeats} repeats; models {models}")
    log(f"MLP class weighting: {'balanced sample weights' if MLP_SUPPORTS_WEIGHTS else 'NONE (scikit-learn < 1.7)'}")
    log("=" * 72)

    # requirements.txt with the exact versions used in this run
    req = config.PROJECT_ROOT / "requirements.txt"
    req.write_text(f"# Exact versions used by the last run_phase1.py (Python {sys.version.split()[0]})\n"
                   + "".join(f"{k}=={v}\n" for k, v in versions().items() if v != "not installed"))

    if not args.skip_analysis:
        import dedup_analysis, feature_space_analysis
        dedup_analysis.main()
        feature_space_analysis.main()

    # ---- Variants --------------------------------------------------------
    log("\nBuilding variants...")
    X_full, y_full, _ = encode(load_raw(config.FULL_CSV))
    variants = [variant_a(), variant_b(X_full, y_full)]
    classes = sorted(y_full.unique())
    to_int = {c: i for i, c in enumerate(classes)}
    feats = list(X_full.columns)
    for v in variants:
        log(f"  Variant {v['name']}: train {len(v['y_train']):,}  test {len(v['y_test']):,}  "
            f"features {v['X_train'].shape[1]}")

    cv_rows, test_rows, class_rows, imp_rows, leak_rows = [], [], [], [], []
    preds = {}

    for v in variants:
        ytr = v["y_train"].map(to_int).to_numpy()
        yte = v["y_test"].map(to_int).to_numpy()
        Xtr, Xte = v["X_train"].to_numpy(), v["X_test"].to_numpy()
        # unique test feature vectors per class -> reliability of per-class scores
        te_keys = row_key(v["X_test"], feats)
        uniq_test = {c: te_keys[v["y_test"].to_numpy() == c].nunique() for c in classes}

        for m in models:
            log(f"\n--- Variant {v['name']} · {m} ---")
            fold_scores = []
            t0 = time.time()
            for k, (tr_i, va_i) in enumerate(cv_splits(v, ytr, args.repeats)):
                tf = time.time()
                model = fit_model(m, Xtr[tr_i], ytr[tr_i])
                s = ev.scores(ytr[va_i], model.predict(Xtr[va_i]), classes)
                fold_scores.append(s)
                log(f"  fold {k + 1:2d}: macro F1 {s['macro_f1']:.4f}  ({time.time() - tf:.1f} s)")
            fs = pd.DataFrame(fold_scores)
            cv_row = {"variant": v["name"], "model": m, "folds": len(fs)}
            for col in fs.columns:
                if col.startswith("support_"):
                    continue
                cv_row[f"{col}_mean"] = fs[col].mean()
                cv_row[f"{col}_std"] = fs[col].std(ddof=1)
            cv_rows.append(cv_row)
            log(f"  CV macro F1 = {fmt(cv_row['macro_f1_mean'], cv_row['macro_f1_std'])}  "
                f"({time.time() - t0:.0f} s for CV)")

            # final model, test set touched once
            tf = time.time()
            model = fit_model(m, Xtr, ytr)
            train_s = time.time() - tf
            yp = model.predict(Xte)
            s = ev.scores(yte, yp, classes)
            preds[(v["name"], m)] = (yte, yp)
            lat_b, lat_1 = ev.latency_ms(model, Xte)
            # Leakage effect: score test rows the model has SEEN in training
            # (identical feature vector in train) separately from UNSEEN rows.
            seen = te_keys.isin(set(row_key(v["X_train"], feats))).to_numpy()
            for part, mask in (("seen_in_train", seen), ("unseen", ~seen)):
                if mask.sum():
                    ps = ev.scores(yte[mask], yp[mask], classes)
                    leak_rows.append({"variant": v["name"], "model": m, "test_subset": part,
                                      "rows": int(mask.sum()),
                                      "share_of_test_pct": round(100 * mask.mean(), 2),
                                      "macro_f1": round(ps["macro_f1"], 4),
                                      "accuracy": round(ps["accuracy"], 4)})
            size_kb = ev.save_model(model, config.MODELS_DIR / f"{m}_variant{v['name']}.joblib")
            log(f"  TEST macro F1 {s['macro_f1']:.4f}  weighted F1 {s['weighted_f1']:.4f}  "
                f"accuracy {s['accuracy']:.4f}  FPR {s['fpr']:.4f}")
            log(f"  train {train_s:.1f} s  latency {lat_b:.5f} ms/sample (batch), "
                f"{lat_1:.3f} ms (single row)  size {size_kb:,.0f} KB")

            test_rows.append({"variant": v["name"], "model": m,
                              "cv_macro_f1": fmt(cv_row["macro_f1_mean"], cv_row["macro_f1_std"]),
                              "cv_weighted_f1": fmt(cv_row["weighted_f1_mean"], cv_row["weighted_f1_std"]),
                              "cv_accuracy": fmt(cv_row["accuracy_mean"], cv_row["accuracy_std"]),
                              "cv_fpr": fmt(cv_row["fpr_mean"], cv_row["fpr_std"]),
                              "test_macro_f1": round(s["macro_f1"], 4),
                              "test_weighted_f1": round(s["weighted_f1"], 4),
                              "test_accuracy": round(s["accuracy"], 4),
                              "test_fpr": round(s["fpr"], 4),
                              "train_time_s": round(train_s, 1),
                              "latency_ms_per_sample_batch": round(lat_b, 5),
                              "latency_ms_single_row": round(lat_1, 3),
                              "model_size_kb": round(size_kb, 1)})
            for c in classes:
                reliable = uniq_test[c] >= config.MIN_UNIQUE_WARN
                class_rows.append({
                    "variant": v["name"], "model": m, "class": c,
                    "test_rows": s[f"support_{c}"], "test_unique_vectors": uniq_test[c],
                    "precision": round(s[f"precision_{c}"], 4),
                    "recall": round(s[f"recall_{c}"], 4), "f1": round(s[f"f1_{c}"], 4),
                    "cv_recall": fmt(cv_row[f"recall_{c}_mean"], cv_row[f"recall_{c}_std"]),
                    "reliability": "ok" if reliable else
                    f"LOW: only {uniq_test[c]} unique test vectors (<{config.MIN_UNIQUE_WARN})"})
            ev.plot_confusion(yte, yp, classes, f"{m} · Variant {v['name']} · test set",
                              config.FIGURES_DIR / f"confusion_{m}_variant{v['name']}.png")
            imp = feature_importance(m, model, feats)
            if imp:
                for f_, val in imp.items():
                    imp_rows.append({"variant": v["name"], "model": m, "feature": f_,
                                     "importance": round(float(val), 6),
                                     "group": "TCP" if f_.startswith("tcp.") else "MQTT",
                                     "o2_constraint": "mutable" if f_ in config.MUTABLE_FIELDS
                                     else "immutable" if f_ in config.IMMUTABLE_FIELDS
                                     else "not yet classified"})
                ev.plot_importance(imp, f"{m} feature importance (top 15) · Variant {v['name']}",
                                   config.FIGURES_DIR / f"importance_{m}_variant{v['name']}.png")

    # ---- Tables ---------------------------------------------------------
    log("\n" + "=" * 72 + "\nRESULTS")
    base = pd.DataFrame(test_rows)
    save_table(base, "baseline_results", log)
    save_table(pd.DataFrame(cv_rows).round(4), "cv_results_detail", log)
    pc = pd.DataFrame(class_rows)
    save_table(pc, "per_class_results", log)
    if imp_rows:
        imp_df = pd.DataFrame(imp_rows).sort_values(["variant", "model", "importance"],
                                                    ascending=[True, True, False])
        save_table(imp_df, "feature_importance", log)

    ab = []
    for m in models:
        a = base[(base.model == m) & (base.variant == "A")].iloc[0]
        b = base[(base.model == m) & (base.variant == "B")].iloc[0]
        ab.append({"model": m, "A_test_macro_f1": a.test_macro_f1, "B_test_macro_f1": b.test_macro_f1,
                   "delta_A_minus_B": round(a.test_macro_f1 - b.test_macro_f1, 4),
                   "A_cv_macro_f1": a.cv_macro_f1, "B_cv_macro_f1": b.cv_macro_f1})
    ab_df = pd.DataFrame(ab)
    save_table(ab_df, "ab_comparison", log)
    leak_df = pd.DataFrame(leak_rows)
    save_table(leak_df, "leakage_effect_seen_vs_unseen", log)
    log("\nTest rows already seen in training vs unseen:")
    log(leak_df.to_string(index=False))
    log("\n" + base[["variant", "model", "cv_macro_f1", "test_macro_f1", "test_accuracy",
                     "test_fpr", "latency_ms_single_row", "model_size_kb"]].to_string(index=False))
    log("\n" + ab_df.to_string(index=False))

    # ---- Figures --------------------------------------------------------
    ev.plot_macro_f1(base.rename(columns={"test_macro_f1": "macro_f1"}),
                     config.FIGURES_DIR / "macro_f1_A_vs_B.png")
    for vn in ("A", "B"):
        best = base[base.variant == vn].sort_values("test_macro_f1", ascending=False).iloc[0]
        r = pc[(pc.variant == vn) & (pc.model == best.model)].set_index("class")["recall"]
        ev.plot_per_class_recall({f"recall_{c}": r[c] for c in classes}, classes,
                                 f"Per-class recall · best model on Variant {vn}: {best.model}",
                                 config.FIGURES_DIR / f"per_class_recall_best_variant{vn}.png")
    log("  figures saved -> results/phase1/figures/")

    # ---- Auto summary ---------------------------------------------------
    md = ["# Phase 1 results (AUTO-GENERATED by run_phase1.py)", "",
          f"Run: {time.strftime('%Y-%m-%d %H:%M:%S')} on {platform.platform()}; "
          f"Python {sys.version.split()[0]}; " + ", ".join(f"{k} {v}" for k, v in versions().items()),
          f"CV: {config.CV_SPLITS} folds x {args.repeats} repeats, seed {config.SEED}. "
          "Test sets used once.", "",
          "Headline metric: macro F1. Accuracy is shown only for comparison with the literature.", "",
          "## A vs B", "", to_markdown(ab_df)]
    md += ["## Seen vs unseen test rows", "", to_markdown(leak_df)]
    md += ["## All results", "", to_markdown(base), "## Per-class (test set)", "", to_markdown(pc),
           "Rows marked LOW have too few unique test vectors for a reliable per-class estimate.", ""]
    (config.RESULTS_DIR / "PHASE1_RESULTS_AUTO.md").write_text("\n".join(md))
    log("  summary -> results/phase1/PHASE1_RESULTS_AUTO.md")
    log(f"\nTOTAL RUNTIME: {(time.time() - t_start) / 60:.1f} min")
    log.save()


if __name__ == "__main__":
    main()
