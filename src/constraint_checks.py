"""
constraint_checks.py — Phase 2 groundwork: test candidate MQTT protocol
constraints against the real data, so the O2 constraint table is evidence-based.

For each rule from the MQTT 3.1.1 specification, count how many rows obey it.
A rule that the data breaks is either wrong or reveals malformed traffic,
and either way must be known before attacks are designed.

Run:  python3 src/constraint_checks.py      (about 30 seconds)
Writes: results/phase2/tables/constraint_rule_checks.csv/.md
        results/phase2/tables/feature_ranges.csv/.md
        results/phase2/tables/packet_types_per_class.csv/.md
        results/phase2/tables/tcp_minus_mqtt_len.csv/.md
"""
import numpy as np
import pandas as pd

import config
from data_loader import encode, load_raw
from utils import Logger, pct, to_markdown

log = Logger("constraint_checks")
OUT = config.PROJECT_ROOT / "results" / "phase2" / "tables"
TYPE_NAMES = {1: "CONNECT", 2: "CONNACK", 3: "PUBLISH", 4: "PUBACK", 5: "PUBREC", 6: "PUBREL",
              7: "PUBCOMP", 8: "SUBSCRIBE", 9: "SUBACK", 10: "UNSUBSCRIBE", 11: "UNSUBACK",
              12: "PINGREQ", 13: "PINGRESP", 14: "DISCONNECT"}


def save(df, name):
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / f"{name}.csv", index=False)
    (OUT / f"{name}.md").write_text(to_markdown(df))
    log(f"  saved -> results/phase2/tables/{name}.csv (+ .md)")


def main():
    raw = load_raw(config.FULL_CSV)
    X, y, _ = encode(raw)
    has_mqtt = X["mqtt.hdrflags"] != config.ABSENT_VALUE
    hdr = X["mqtt.hdrflags"].where(has_mqtt, 0).astype(int)
    mtype = X["mqtt.msgtype"].astype(int)
    pub = has_mqtt & (mtype == 3)
    con = has_mqtt & (mtype == 1)
    qos, dup, ret = X["mqtt.qos"].astype(int), X["mqtt.dupflag"].astype(int), X["mqtt.retain"].astype(int)

    rules = []

    def rule(name, scope_mask, ok_mask, source):
        n = int(scope_mask.sum()); k = int((scope_mask & ok_mask).sum())
        rules.append({"rule": name, "applies_to_rows": n, "rows_obeying": k,
                      "obey_pct": pct(k, n), "basis": source})

    rule("packet type = upper 4 bits of mqtt.hdrflags", has_mqtt, (hdr // 16) == mtype,
         "MQTT 3.1.1 §2.2.1")
    rule("PUBLISH: low 4 bits of hdrflags = DUP<<3 | QoS<<1 | RETAIN", pub,
         (hdr % 16) == (dup * 8 + qos * 2 + ret), "MQTT 3.1.1 §3.3.1")
    rule("PUBLISH: message ID present (non-zero) only if QoS > 0", pub,
         (X["mqtt.msgid"] > 0) == (qos > 0), "MQTT 3.1.1 §2.3.1")
    rule("PUBLISH: DUP = 1 only if QoS > 0", pub, ~((dup == 1) & (qos == 0)), "MQTT 3.1.1 §3.3.1.1")
    rule("CONNECT: conflags = uname<<7 | passwd<<6 | cleansess<<1", con,
         X["mqtt.conflags"].astype(int) == (X["mqtt.conflag.uname"].astype(int) * 128
                                            + X["mqtt.conflag.passwd"].astype(int) * 64
                                            + X["mqtt.conflag.cleansess"].astype(int) * 2),
         "MQTT 3.1.1 §3.1.2.3 (will flags are constant 0 in this data)")
    rule("CONNECT: password flag = 1 only if username flag = 1", con,
         ~((X["mqtt.conflag.passwd"] == 1) & (X["mqtt.conflag.uname"] == 0)), "MQTT 3.1.1 §3.1.2.9")
    rule("CONNECT: protoname = 'MQTT', proto_len = 4, ver = 4", con,
         (X["mqtt.protoname"] == 1) & (X["mqtt.proto_len"] == 4) & (X["mqtt.ver"] == 4),
         "MQTT 3.1.1 §3.1.2.1-2")
    rule("protoname / proto_len / ver / kalive / conflags appear only in CONNECT", ~con,
         (X["mqtt.protoname"] == 0) & (X["mqtt.proto_len"] == 0) & (X["mqtt.ver"] == 0)
         & (X["mqtt.kalive"] == 0) & (X["mqtt.conflags"] == config.ABSENT_VALUE),
         "packet structure")
    conack = has_mqtt & (mtype == 2)
    rule("conack.flags / conack.val appear only in CONNACK", ~conack,
         (X["mqtt.conack.flags"] == config.ABSENT_VALUE) & (X["mqtt.conack.val"] == 0),
         "packet structure")
    rule("rows with no MQTT header have every MQTT field absent/zero", ~has_mqtt,
         (X["mqtt.msgtype"] == 0) & (X["mqtt.len"] == 0) & (X["mqtt.msgid"] == 0)
         & (X["mqtt.qos"] == 0), "packet structure")
    rule("MQTT rows: tcp.len >= mqtt.len + 2 (header + length byte)", has_mqtt,
         X["tcp.len"] >= X["mqtt.len"] + 2, "MQTT 3.1.1 §2.2.3 (min. fixed header)")
    rule("MQTT rows: tcp.len == mqtt.len + 2 (exactly one small MQTT packet per segment)", has_mqtt,
         X["tcp.len"] == X["mqtt.len"] + 2, "one packet, remaining length < 128")

    rdf = pd.DataFrame(rules)
    log("\nRULE CHECKS")
    log(rdf.to_string(index=False))
    save(rdf, "constraint_rule_checks")

    # tcp.len - mqtt.len distribution on MQTT rows
    d = (X.loc[has_mqtt, "tcp.len"] - X.loc[has_mqtt, "mqtt.len"]).astype(int)
    dd = d.value_counts().head(10).rename_axis("tcp_len_minus_mqtt_len").reset_index(name="rows")
    dd["share_pct"] = (100 * dd["rows"] / len(d)).round(2)
    log("\ntcp.len - mqtt.len on MQTT rows (top 10 values)")
    log(dd.to_string(index=False))
    save(dd, "tcp_minus_mqtt_len")

    # value ranges
    rng = pd.DataFrame([{"feature": c, "min": X[c].min(), "max": X[c].max(),
                         "distinct": X[c].nunique(),
                         "values_if_few": ", ".join(str(int(v)) if float(v).is_integer() else str(v)
                                                    for v in sorted(X[c].unique())[:8])
                         if X[c].nunique() <= 8 else ""} for c in X.columns])
    log("\nFEATURE RANGES")
    log(rng.to_string(index=False))
    save(rng, "feature_ranges")

    # packet types per class
    t = pd.Series(np.where(has_mqtt, mtype.map(TYPE_NAMES).fillna("type " + mtype.astype(str)),
                           "no MQTT (bare TCP)"))
    pt = pd.crosstab(t, y).reset_index().rename(columns={"row_0": "packet_type"})
    pt.columns = ["packet_type"] + list(pt.columns[1:])
    log("\nPACKET TYPES PER CLASS (rows)")
    log(pt.to_string(index=False))
    save(pt, "packet_types_per_class")

    # keep-alive per class (CONNECT rows)
    ka = pd.crosstab(X.loc[con, "mqtt.kalive"].astype(int), y[con])
    log("\nKEEP-ALIVE VALUES IN CONNECT PACKETS, per class")
    log(ka.to_string())
    qq = pd.crosstab(qos[pub], y[pub])
    log("\nQoS IN PUBLISH PACKETS, per class")
    log(qq.to_string())
    log.save()


if __name__ == "__main__":
    main()
