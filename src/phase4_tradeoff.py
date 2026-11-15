"""
phase4_tradeoff.py — Objective O4: the robustness / accuracy / cost trade-off.

    python3 src/phase4_tradeoff.py       # after phase2 and phase3 have run

This does not train anything new. It joins the numbers already produced:
  - clean macro F1 (undefended and defended)      from O1 / O3
  - robustness = 100 - adaptive re-attack ASR      from O2 / O3
  - inference latency and model size on disk        measured here, CPU-only
and writes one table and one figure showing, per model, what adversarial
training costs in clean accuracy and inference cost, and what it buys in
robustness. This is the deployability view the report (3.8) and the panel ask for.

Robustness is averaged over attack classes for the given constraint set.
"""
import argparse
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
import evaluate as ev
from data_loader import encode, load_raw, variant_b
from models import fit_model
from phase2_attacks import run_attack
from phase3_defence import load_adv
from utils import Logger, save_table

log = Logger("phase4_tradeoff")


def robustness(model, Xte, yte, classes, cset, budget, per_class):
    rows, _, _ = run_attack(model, Xte, yte, classes, cset, budget, per_class,
                            np.random.default_rng(config.SEED))
    asr = [r["attack_success_rate"] for r in rows if r.get("evaluated", 0) > 0]
    return round(100 - float(np.mean(asr)), 2) if asr else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=120)
    ap.add_argument("--per-class", type=int, default=800)
    ap.add_argument("--set", default="extended", help="constraint set for the robustness axis")
    args = ap.parse_args()
    t0 = time.time()

    X, y, _ = encode(load_raw(config.FULL_CSV))
    vb = variant_b(X, y)
    classes = sorted(y.unique())
    to_int = {c: i for i, c in enumerate(classes)}
    Xtr, ytr = vb["X_train"].to_numpy(), vb["y_train"].map(to_int).to_numpy()
    Xte, yte = vb["X_test"].to_numpy(), vb["y_test"].map(to_int).to_numpy()
    cset = args.set

    log("=" * 72)
    log(f"PHASE 4 (O4) — ROBUSTNESS / ACCURACY / COST  (constraint set: {cset})")
    log("=" * 72)

    rows = []
    for mname in ("RandomForest", "XGBoost", "MLP"):
        for defended in (False, True):
            if defended:
                advX, advY = load_adv(mname, cset)
                if advX is None:
                    continue
                rs = np.random.default_rng(config.SEED)
                tr_i = rs.permutation(len(advX))[: len(advX) // 2]
                Xf = np.vstack([Xtr, advX[tr_i]]); yf = np.concatenate([ytr, advY[tr_i]])
            else:
                Xf, yf = Xtr, ytr
            model = fit_model(mname, Xf, yf)
            f1 = ev.scores(yte, model.predict(Xte), classes)["macro_f1"]
            lat_b, lat_1 = ev.latency_ms(model, Xte)
            size_kb = ev.save_model(model, config.MODELS_DIR / f"o4_{mname}_{'def' if defended else 'base'}.joblib")
            rob = robustness(model, Xte, yte, classes, cset, args.budget, args.per_class)
            rows.append({"model": mname, "variant": "defended" if defended else "baseline",
                         "clean_macro_f1": round(f1, 4), "robustness_pct": rob,
                         "latency_ms_per_packet": round(lat_1, 3), "model_size_kb": round(size_kb, 1)})
            log(f"  {mname:12s} {'defended' if defended else 'baseline':9s}  F1 {f1:.4f}  "
                f"robustness {rob}%  latency {lat_1:.3f} ms  size {size_kb:,.0f} KB")

    df = pd.DataFrame(rows)
    save_table(df, "o4_tradeoff", log, subdir="phase4")

    # scatter: robustness (x) vs clean F1 (y); marker size ~ model size; arrow base->defended
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    col = {"RandomForest": "#1f5f7a", "XGBoost": "#c0392b", "MLP": "#2e7d4f"}
    for m in df.model.unique():
        sub = df[df.model == m]
        for _, r in sub.iterrows():
            ax.scatter(r.robustness_pct, r.clean_macro_f1, s=60 + r.model_size_kb / 200,
                       c=col[m], marker="o" if r.variant == "baseline" else "D",
                       edgecolor="black", linewidth=0.5, zorder=3,
                       label=f"{m}" if r.variant == "baseline" else None)
        if len(sub) == 2:
            b = sub[sub.variant == "baseline"].iloc[0]; d = sub[sub.variant == "defended"].iloc[0]
            ax.annotate("", xy=(d.robustness_pct, d.clean_macro_f1),
                        xytext=(b.robustness_pct, b.clean_macro_f1),
                        arrowprops=dict(arrowstyle="->", color=col[m], alpha=0.6))
    ax.set_xlabel(f"Robustness: 100 − adaptive attack success rate (%)  [{cset} constraint set]")
    ax.set_ylabel("Clean macro F1")
    ax.set_title("O4: robustness vs clean accuracy\n○ baseline  ◇ adversarially trained  (marker size ~ model size)",
                 fontsize=11)
    ax.legend(frameon=False); ax.grid(alpha=0.25); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(config.FIGURES_DIR / "o4_tradeoff.png", dpi=config.FIG_DPI); plt.close(fig)
    log("  figure -> results/phase1/figures/o4_tradeoff.png")
    log("\n" + df.to_string(index=False))
    log(f"\nTotal {(time.time()-t0)/60:.1f} min")
    log.save()


if __name__ == "__main__":
    main()
