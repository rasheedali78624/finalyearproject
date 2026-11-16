"""
phase2_attacks.py — Objective O2: constraint-aware adversarial evasion.

    python3 src/phase2_attacks.py                 # all models, both constraint sets
    python3 src/phase2_attacks.py --budget 150 --per-class 1500

Threat model (from the report, Table 3.4): a GREY-BOX adversary. It knows the
feature representation and that a detector exists, but not the model's trained
parameters. So it cannot compute gradients. It searches: it proposes allowed,
protocol-valid changes to an attack packet and observes only the detector's
decision (a decision-based black-box search), keeping within a query budget.

Only MQTT packets the attacker itself sends are attacked (CONNECT, PUBLISH,
SUBSCRIBE, ...). Bare TCP rows and broker replies are left alone; the table
counts them (detected_rows vs attacker_packets). See constraints.py.

For each attack record the trained model classifies correctly, the attacker
tries to make the model output "legitimate" by changing ONLY the fields its
constraint set allows (constraints.py), updating dependent fields, and keeping
the packet protocol-valid. Success = the perturbed, still-valid packet is
classified legitimate.

Reported (report Table 3.6):
  - Attack success rate (ASR): share of attack samples driven to "legitimate"
  - Detection recall, clean vs adversarial, and its degradation (the main result)
  - Mean queries and mean fields changed (attack cost / realism)
  - Protocol-validity rate of generated candidates (every retained sample is valid)
All per attack class, per model, for the "report" and "extended" constraint sets.

Writes results/phase2/tables/ and results/phase2/attacks/<model>_<set>.npz
(the adversarial feature vectors, reused by O3).
"""
import argparse
import time

import numpy as np
import pandas as pd

import config
import constraints as K
from data_loader import encode, load_raw, variant_b
from models import fit_model
from utils import Logger, pct, save_table

log = Logger("phase2_attacks")
ATTACK_CLASSES = ["dos", "flood", "bruteforce", "malformed", "slowite"]


def candidate_changes(constraint_set, rng, n_random):
    """A list of change-dicts to try, from a small guided grid plus random fills."""
    td = [0.001, 0.01, 0.1, 1.0, 10.0, K.TIME_DELTA_CAP]      # add delay
    pad = [0, 4, 16, 64, 256]                                  # extra padding bytes
    ka = [10, 60, 300, 3600, 65535]                            # keep-alive (CONNECT only)
    grid = []
    for t in td:
        grid.append({"tcp.time_delta": t})
    for p in pad[1:]:
        grid.append({"mqtt.len": ("add", p)})
        grid.append({"tcp.time_delta": 1.0, "mqtt.len": ("add", p)})
    for k in ka:
        grid.append({"mqtt.kalive": k})
    if constraint_set == "extended":
        for q in (0, 1):
            for r in (0, 1):
                grid.append({"mqtt.qos": q, "mqtt.retain": r})
                grid.append({"mqtt.qos": q, "mqtt.retain": r, "tcp.time_delta": 1.0})
    # random fills within the allowed space
    for _ in range(n_random):
        c = {"tcp.time_delta": float(rng.choice(td)), "mqtt.len": ("add", int(rng.choice(pad)))}
        if constraint_set == "extended":
            c["mqtt.qos"] = int(rng.integers(0, 2)); c["mqtt.retain"] = int(rng.integers(0, 2))
        grid.append(c)
    return grid


def build_candidate(x, change):
    """Resolve a change-dict (handling ('add', n) padding) into a concrete vector."""
    resolved = {}
    for f, val in change.items():
        if isinstance(val, tuple) and val[0] == "add":
            resolved[f] = x[K.IDX["mqtt.len"]] + val[1]
        else:
            resolved[f] = val
    return K.apply_perturbation(x, resolved)


def attack_record(x, model, legit_int, grid, budget, attack_class=None):
    """
    Try to flip one record to legitimate within `budget` queries.
    Returns (success, queries_used, best_vector_or_None).
    One model.predict call covers the whole valid candidate batch (fast).
    """
    cands, used = [], 0
    for ch in grid:
        if used >= budget:
            break
        xc = build_candidate(x, ch)
        # skip candidates that are invalid or change nothing (e.g. padding a
        # packet type that cannot be padded)
        if K.is_protocol_valid(x, xc, attack_class) and K.n_changed_features(x, xc) > 0:
            cands.append(xc); used += 1
    if not cands:
        return False, 0, None
    preds = model.predict(np.array(cands))
    hit = np.where(preds == legit_int)[0]
    if len(hit):
        return True, int(hit[0]) + 1, cands[int(hit[0])]
    return False, used, None


def run_attack(model, Xte, yte_int, classes, constraint_set, budget, per_class, rng):
    legit_int = classes.index(config.NORMAL_CLASS)
    grid = candidate_changes(constraint_set, rng, n_random=max(0, budget))
    rows, adv_vectors, adv_meta = [], [], []
    for cls in ATTACK_CLASSES:
        ci = classes.index(cls)
        # source population: this attack, correctly detected as NOT legitimate
        idx = np.where((yte_int == ci) & (model.predict(Xte) != legit_int))[0]
        n_detected = len(idx)
        # only MQTT packets the attacker sends can be reshaped (constraints.py);
        # bare TCP rows and broker replies are counted but not attacked
        idx = np.array([i for i in idx if K.in_attack_scope(Xte[i])], dtype=int)
        n_scope = len(idx)
        if len(idx) == 0:
            rows.append({"constraint_set": constraint_set, "class": cls,
                         "detected_rows": n_detected, "attacker_packets": 0, "evaluated": 0,
                         "note": "no correctly-detected attacker-sent packets"}); continue
        if len(idx) > per_class:
            idx = rng.choice(idx, per_class, replace=False)
        succ = q_used = chg = 0
        for i in idx:
            ok, q, best = attack_record(Xte[i], model, legit_int, grid, budget, cls)
            q_used += q
            if ok:
                succ += 1; chg += K.n_changed_features(Xte[i], best)
                adv_vectors.append(best); adv_meta.append(ci)
        n = len(idx)
        rows.append({"constraint_set": constraint_set, "class": cls,
                     "detected_rows": n_detected, "attacker_packets": n_scope, "evaluated": n,
                     "evasions": succ, "attack_success_rate": pct(succ, n),
                     "clean_recall": 1.0,  # source is correctly detected by construction
                     "adversarial_recall": round(1 - succ / n, 4),
                     "recall_degradation": round(succ / n, 4),
                     "mean_queries": round(q_used / n, 1),
                     "mean_fields_changed": round(chg / succ, 2) if succ else 0.0})
    return rows, adv_vectors, adv_meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=120)
    ap.add_argument("--per-class", type=int, default=1200)
    ap.add_argument("--models", default="RandomForest,XGBoost,MLP")
    ap.add_argument("--sets", default="report,extended")
    args = ap.parse_args()
    rng = np.random.default_rng(config.SEED)
    t0 = time.time()
    (config.PROJECT_ROOT / "results" / "phase2" / "attacks").mkdir(parents=True, exist_ok=True)

    log("=" * 72)
    log("PHASE 2 (O2) — CONSTRAINT-AWARE ADVERSARIAL EVASION")
    log(f"Grey-box decision-based search; budget {args.budget}; up to {args.per_class}/class")
    log("=" * 72)

    X, y, _ = encode(load_raw(config.FULL_CSV))
    vb = variant_b(X, y)
    classes = sorted(y.unique())
    to_int = {c: i for i, c in enumerate(classes)}
    Xtr, ytr = vb["X_train"].to_numpy(), vb["y_train"].map(to_int).to_numpy()
    Xte, yte = vb["X_test"].to_numpy(), vb["y_test"].map(to_int).to_numpy()
    log(f"Variant B (de-duplicated): train {len(ytr):,}  test {len(yte):,}  features {Xtr.shape[1]}")
    assert list(vb["X_train"].columns) == K.FEATURES, "feature order mismatch with constraints.py"

    all_rows = []
    for mname in [m.strip() for m in args.models.split(",")]:
        log(f"\n### Target model: {mname} ###")
        model = fit_model(mname, Xtr, ytr)
        for cset in [c.strip() for c in args.sets.split(",")]:
            tS = time.time()
            rows, adv, meta = run_attack(model, Xte, yte, classes, cset, args.budget,
                                         args.per_class, np.random.default_rng(config.SEED))
            for r in rows:
                r["model"] = mname
                log("  " + "  ".join(f"{k}={v}" for k, v in r.items()
                                     if k in ("constraint_set", "class", "evaluated",
                                              "attack_success_rate", "mean_queries", "mean_fields_changed")))
            all_rows += rows
            # remove any file from an earlier run first, so O3 never trains on stale samples
            npz = config.PROJECT_ROOT / "results" / "phase2" / "attacks" / f"{mname}_{cset}.npz"
            npz.unlink(missing_ok=True)
            if adv:
                np.savez_compressed(npz, X=np.array(adv), y=np.array(meta))
            log(f"  [{mname}/{cset}] {len(adv)} adversarial samples kept  ({time.time()-tS:.0f}s)")

    df = pd.DataFrame(all_rows)
    cols = ["model", "constraint_set", "class", "detected_rows", "attacker_packets",
            "evaluated", "evasions",
            "attack_success_rate", "clean_recall", "adversarial_recall",
            "recall_degradation", "mean_queries", "mean_fields_changed"]
    df = df[[c for c in cols if c in df.columns]]
    save_table(df, "o2_attack_results", log, subdir="phase2")
    log("\n" + df.to_string(index=False))
    log(f"\nTotal {(time.time()-t0)/60:.1f} min")
    log.save()


if __name__ == "__main__":
    main()
