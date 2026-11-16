"""
phase3_defence.py — Objective O3: a constraint-aware robust detection framework,
evaluated under ADAPTIVE re-attack.

    python3 src/phase3_defence.py                 # after phase2_attacks.py has run
    python3 src/phase3_defence.py --budget 120 --per-class 1200

Primary defence: ADVERSARIAL TRAINING. The successful adversarial samples from
O2 (saved by phase2_attacks.py) are added to the training set, labelled with
their TRUE attack class, and the model is retrained. The model thus learns that
these perturbed packets are still attacks.

Secondary defence (optional, report 3.7): FEATURE HARDENING. Retrain without the
fields the attacker most exploits, so the detector cannot lean on an
attacker-controlled shortcut. Enabled with --harden.

The decisive test (report 3.7, and the gap most papers omit): ADAPTIVE RE-ATTACK.
The same O2 search is run AGAIN against the hardened model, by an attacker that
now faces the defended detector. A defence only counts if it holds here, not
merely against the original samples.

Reported per model and constraint set:
  clean macro F1 (undefended vs defended)       -- cost of the defence
  ASR of the original attack on the defended model  -- static robustness
  ASR of the adaptive re-attack on the defended model -- true robustness
Writes results/phase3/tables/.
"""
import argparse
import time

import numpy as np
import pandas as pd

import config
import constraints as K
import evaluate as ev
from data_loader import encode, load_raw, variant_b
from models import fit_model
from phase2_attacks import ATTACK_CLASSES, run_attack
from utils import Logger, pct, save_table

log = Logger("phase3_defence")
# Fields hardening removes: the semantic shortcut (Phase 1) plus its dependents.
HARDEN_DROP = ["mqtt.qos", "mqtt.msgid", "mqtt.hdrflags"]


def load_adv(mname, cset):
    p = config.PROJECT_ROOT / "results" / "phase2" / "attacks" / f"{mname}_{cset}.npz"
    if not p.exists():
        return None, None
    d = np.load(p)
    return d["X"], d["y"]


def macro_f1(model, X, y_int, classes):
    return ev.scores(y_int, model.predict(X), classes)["macro_f1"]


def asr_on(model, Xte, yte, classes, cset, budget, per_class):
    """Attack success rate of a fresh O2 search against `model`, averaged over attack classes."""
    rows, _, _ = run_attack(model, Xte, yte, classes, cset, budget, per_class,
                            np.random.default_rng(config.SEED))
    vals = [r["attack_success_rate"] for r in rows if r.get("evaluated", 0) > 0
            and "attack_success_rate" in r]
    return round(float(np.mean(vals)), 2) if vals else float("nan"), rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=120)
    ap.add_argument("--per-class", type=int, default=1200)
    ap.add_argument("--models", default="RandomForest,XGBoost,MLP")
    ap.add_argument("--sets", default="report,extended")
    ap.add_argument("--harden", action="store_true", help="also run feature-hardening defence")
    args = ap.parse_args()
    t0 = time.time()

    X, y, _ = encode(load_raw(config.FULL_CSV))
    vb = variant_b(X, y)
    classes = sorted(y.unique())
    to_int = {c: i for i, c in enumerate(classes)}
    Xtr, ytr = vb["X_train"].to_numpy(), vb["y_train"].map(to_int).to_numpy()
    Xte, yte = vb["X_test"].to_numpy(), vb["y_test"].map(to_int).to_numpy()

    log("=" * 72)
    log("PHASE 3 (O3) — ADVERSARIAL TRAINING + ADAPTIVE RE-ATTACK")
    log(f"budget {args.budget}; up to {args.per_class}/class; harden={args.harden}")
    log("=" * 72)

    rows = []
    for mname in [m.strip() for m in args.models.split(",")]:
        base = fit_model(mname, Xtr, ytr)
        base_f1 = macro_f1(base, Xte, yte, classes)
        log(f"\n### {mname} — clean macro F1 (undefended) = {base_f1:.4f} ###")
        for cset in [c.strip() for c in args.sets.split(",")]:
            advX, advY = load_adv(mname, cset)
            if advX is None:
                log(f"  [{cset}] no O2 evasion samples for this model/set (the attack found none, or phase2_attacks.py has not run)"); continue
            # Split O2 samples: half to train the defence, half held out to measure
            # whether the OLD samples still evade (static robustness). This avoids
            # evaluating the defence on its own training data.
            rs = np.random.default_rng(config.SEED)
            perm = rs.permutation(len(advX)); half = len(advX) // 2
            tr_i, te_i = perm[:half], perm[half:]
            legit_int = classes.index(config.NORMAL_CLASS)

            # --- adversarial training: add O2 samples with their TRUE labels ---
            Xat = np.vstack([Xtr, advX[tr_i]]); yat = np.concatenate([ytr, advY[tr_i]])
            adv_model = fit_model(mname, Xat, yat)
            adv_f1 = macro_f1(adv_model, Xte, yte, classes)
            # static robustness: do the held-out original adversarial samples still evade?
            static_asr = (pct(int(np.sum(adv_model.predict(advX[te_i]) == legit_int)), len(te_i))
                          if len(te_i) else float("nan"))
            # adaptive re-attack: attacker re-runs the search against the defended model
            adaptive_asr, _ = asr_on(adv_model, Xte, yte, classes, cset, args.budget, args.per_class)
            row = {"model": mname, "constraint_set": cset, "defence": "adversarial_training",
                   "clean_f1_undefended": round(base_f1, 4), "clean_f1_defended": round(adv_f1, 4),
                   "clean_f1_change": round(adv_f1 - base_f1, 4),
                   "static_asr_old_samples": static_asr, "adaptive_reattack_asr": adaptive_asr,
                   "adv_samples_trained": len(tr_i)}
            rows.append(row)
            log(f"  [{cset}] adv-trained macro F1 {adv_f1:.4f} (change {adv_f1-base_f1:+.4f}); "
                f"static ASR {static_asr}%  adaptive re-attack ASR {adaptive_asr}%")

            if args.harden:
                keep = [i for i, f in enumerate(K.FEATURES) if f not in HARDEN_DROP]
                hm = fit_model(mname, Xat[:, keep], yat)

                # hardened model sees a reduced feature space; wrap predict to slice
                class Sliced:
                    def __init__(s, m, k): s.m, s.k = m, k
                    def predict(s, Z): return s.m.predict(np.asarray(Z)[:, s.k])
                hmw = Sliced(hm, keep)
                h_f1 = macro_f1(hmw, Xte, yte, classes)
                h_static = (pct(int(np.sum(hmw.predict(advX[te_i]) == legit_int)), len(te_i))
                            if len(te_i) else float("nan"))
                h_asr, _ = asr_on(hmw, Xte, yte, classes, cset, args.budget, args.per_class)
                rows.append({"model": mname, "constraint_set": cset,
                             "defence": "adv_training+feature_hardening",
                             "clean_f1_undefended": round(base_f1, 4),
                             "clean_f1_defended": round(h_f1, 4),
                             "clean_f1_change": round(h_f1 - base_f1, 4),
                             "static_asr_old_samples": h_static, "adaptive_reattack_asr": h_asr,
                             "adv_samples_trained": len(tr_i)})
                log(f"  [{cset}] +hardening macro F1 {h_f1:.4f} "
                    f"(change {h_f1-base_f1:+.4f}); adaptive re-attack ASR {h_asr}%")

    df = pd.DataFrame(rows)
    save_table(df, "o3_defence_results", log, subdir="phase3")
    log("\n" + df.to_string(index=False))
    log(f"\nTotal {(time.time()-t0)/60:.1f} min")
    log.save()


if __name__ == "__main__":
    main()
