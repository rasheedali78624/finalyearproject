"""
o2_validity_audit.py — what KIND of packets are the successful O2 evasions?

The O2 attack runs on every attack row of Variant B. But not every row is a
packet an attacker could really reshape:
  - "bare TCP" rows carry no MQTT packet at all (mqtt.msgtype = 0);
  - some MQTT packets are replies sent by the BROKER, not by the attacker
    (CONNACK, PUBACK, PUBREC, SUBACK, UNSUBACK, PINGRESP);
  - some packet types have a FIXED length in MQTT 3.1.1, so "padding" them
    is not possible (e.g. PINGREQ is always length 0, CONNACK always 2).

This script sorts every saved adversarial sample into one of four groups, so
we know how much of each attack success rate rests on realistic changes:

  impossible_length  mqtt.len > 0 with no MQTT packet, or a fixed-length
                     packet type with the wrong length
  broker_sent        a reply packet type the attacker does not send
  bare_tcp           no MQTT packet, length untouched (only timing can differ)
  attacker_mqtt      an MQTT packet the attacker sends, with a possible length

The same sorting is applied to the CLEAN attack rows of the Variant B test set
as a baseline, because the dataset itself may contain odd rows (the
`malformed` class breaks protocol rules on purpose).

Needs the samples saved by phase2_attacks.py (results/phase2/attacks/*.npz).
Run:  python3 src/o2_validity_audit.py      (under a minute; trains nothing)

Writes: results/phase2/tables/o2_validity_audit.csv/.md
"""
import numpy as np
import pandas as pd

import config
import constraints as K
from data_loader import encode, load_raw, variant_b
from utils import Logger, pct, save_table

log = Logger("o2_validity_audit")

ATTACK_DIR = config.PROJECT_ROOT / "results" / "phase2" / "attacks"
# MQTT 3.1.1 packet types (section 2.2.1)
BROKER_SENT = {2, 4, 5, 9, 11, 13}          # CONNACK PUBACK PUBREC SUBACK UNSUBACK PINGRESP
FIXED_LEN = {2: 2, 4: 2, 5: 2, 6: 2, 7: 2, 11: 2, 12: 0, 13: 0, 14: 0}
GROUPS = ["impossible_length", "broker_sent", "bare_tcp", "attacker_mqtt"]


def group_of(X):
    """One group name per row of X (rows are encoded feature vectors)."""
    mtype = np.rint(X[:, K.IDX["mqtt.msgtype"]]).astype(int)
    mlen = np.rint(X[:, K.IDX["mqtt.len"]]).astype(int)
    out = np.full(len(X), "attacker_mqtt", dtype=object)
    out[mtype == 0] = "bare_tcp"
    out[np.isin(mtype, list(BROKER_SENT))] = "broker_sent"
    bad = (mtype == 0) & (mlen > 0)
    for t, n in FIXED_LEN.items():
        bad |= (mtype == t) & (mlen != n)
    out[bad] = "impossible_length"
    return out


def count_rows(source, cset, classes, X, y_int):
    rows = []
    g = group_of(X)
    for ci, cls in enumerate(classes):
        if cls == config.NORMAL_CLASS:
            continue
        m = y_int == ci
        n = int(m.sum())
        row = {"source": source, "constraint_set": cset, "class": cls, "samples": n}
        for name in GROUPS:
            k = int(np.sum(g[m] == name))
            row[name] = k
            row[f"{name}_pct"] = pct(k, n)
        rows.append(row)
    return rows


def main():
    log("=" * 72)
    log("O2 VALIDITY AUDIT — what kind of packet is each successful evasion?")
    log("=" * 72)
    files = sorted(ATTACK_DIR.glob("*.npz"))
    if not files:
        raise SystemExit(f"No O2 samples in {ATTACK_DIR}. Run src/run_phase2to4.py first.")

    X, y, _ = encode(load_raw(config.FULL_CSV))
    if list(X.columns) != K.FEATURES:
        raise SystemExit("Feature order differs from constraints.FEATURES — stop.")
    classes = sorted(y.unique())
    to_int = {c: i for i, c in enumerate(classes)}
    vb = variant_b(X, y)

    rows = count_rows("clean test rows (baseline)", "-", classes,
                      vb["X_test"].to_numpy(), vb["y_test"].map(to_int).to_numpy())
    for f in files:
        model, cset = f.stem.rsplit("_", 1)
        d = np.load(f)
        rows += count_rows(f"{model} evasions", cset, classes, d["X"], d["y"])

    df = pd.DataFrame(rows)
    save_table(df, "o2_validity_audit", log, subdir="phase2")
    show = ["source", "constraint_set", "class", "samples"] + GROUPS
    log("\nCounts:")
    log(df[show].to_string(index=False))
    log("\nShare of each row's samples (%):")
    log(df[["source", "constraint_set", "class", "samples"]
           + [f"{g}_pct" for g in GROUPS]].to_string(index=False))
    log.save()


if __name__ == "__main__":
    main()
