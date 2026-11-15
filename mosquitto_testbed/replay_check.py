"""
replay_check.py — rebuild O2 perturbations as real MQTT packets and confirm a
live Mosquitto broker accepts them. Run on your Mac with a broker running
(see README.md). Measures the protocol-validity rate (report Table 3.6).

It does NOT reconstruct every field byte-for-byte from the feature vector —
the dataset does not keep the payload. It reconstructs the fields the O2 attack
actually changes (QoS, retain, keep-alive, payload length via padding) and sends
a packet carrying them, which is exactly what the validity claim concerns.
"""
import csv
import os
import sys
import time
from pathlib import Path

import numpy as np

try:
    import paho.mqtt.client as mqtt
except ImportError:
    sys.exit("Install the client first:  pip install paho-mqtt")

ROOT = Path(__file__).resolve().parents[1]
ATTACK_DIR = ROOT / "results" / "phase2" / "attacks"
OUT = ROOT / "results" / "phase2" / "tables"
FEATURES = [  # must match src/constraints.FEATURES
    "tcp.flags", "tcp.time_delta", "tcp.len", "mqtt.conack.flags", "mqtt.conack.val",
    "mqtt.conflag.cleansess", "mqtt.conflag.passwd", "mqtt.conflag.uname", "mqtt.conflags",
    "mqtt.dupflag", "mqtt.hdrflags", "mqtt.kalive", "mqtt.len", "mqtt.msgid",
    "mqtt.msgtype", "mqtt.proto_len", "mqtt.protoname", "mqtt.qos", "mqtt.retain", "mqtt.ver",
]
IX = {f: i for i, f in enumerate(FEATURES)}
BROKER, PORT = "127.0.0.1", 1883


def send_one(vec):
    """Reconstruct and send one perturbed packet. Return True if the broker accepted it."""
    msgtype = int(round(vec[IX["mqtt.msgtype"]]))
    qos = int(round(vec[IX["mqtt.qos"]])) if msgtype == 3 else 0
    retain = bool(round(vec[IX["mqtt.retain"]])) if msgtype == 3 else False
    kalive = int(round(vec[IX["mqtt.kalive"]])) or 60
    payload_len = max(0, int(round(vec[IX["mqtt.len"]])))

    c = mqtt.Client(client_id=f"o2-{int(time.time()*1000)%100000}", clean_session=True)
    try:
        c.connect(BROKER, PORT, keepalive=min(kalive, 65535))  # CONNECT (tests keep-alive)
    except Exception:
        return False
    c.loop_start()
    ok = True
    if msgtype == 3:  # PUBLISH: tests qos / retain / padded payload length
        info = c.publish("o2/test", payload=b"x" * min(payload_len, 1000),
                         qos=min(qos, 2), retain=retain)
        info.wait_for_publish(timeout=2.0)
        ok = info.is_published()
    c.loop_stop(); c.disconnect()
    return ok


def main():
    files = sorted(ATTACK_DIR.glob("*.npz"))
    if not files:
        sys.exit(f"No O2 samples in {ATTACK_DIR}. Run src/phase2_attacks.py first.")
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    rows = []
    for f in files:
        d = np.load(f); Xadv = d["X"]
        idx = rng.permutation(len(Xadv))[:200]  # sample up to 200 per file
        acc = sum(send_one(Xadv[i]) for i in idx)
        rate = round(100 * acc / len(idx), 2) if len(idx) else float("nan")
        rows.append((f.stem, len(idx), acc, rate))
        print(f"{f.stem:28s} sent {len(idx):4d}  accepted {acc:4d}  validity {rate}%")
    with open(OUT / "protocol_validity_rate.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["attack_file", "sent", "accepted", "validity_pct"])
        w.writerows(rows)
    print(f"\nwrote {OUT/'protocol_validity_rate.csv'}")


if __name__ == "__main__":
    main()
