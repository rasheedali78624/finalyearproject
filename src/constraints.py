"""
constraints.py — Phase 2/3 shared: the MQTT constraint set Omega and the
protocol-validity checker, both defined over the 20 encoded features.

This is the code form of the report's Table 3.5 (constraint set) and the
MQTT 3.1.1 structural rules verified in constraint_checks.py. Everything an
adversary is allowed to do, and every rule a perturbed packet must still obey,
is defined here, so O2 (attacks) and O3 (defence) share one source of truth.

Two constraint sets are provided:
  "report"   — exactly Table 3.5: the attacker may change timing, padding and
               keep-alive only (tcp.time_delta, mqtt.len with tcp.len, mqtt.kalive).
  "extended" — report set PLUS the semantic levers Phase 1 showed the detector
               leans on (mqtt.qos, mqtt.retain), with their dependent fields
               (mqtt.msgid, mqtt.hdrflags) updated so the packet stays valid.
The gap between the two measures how much detection depends on those levers.

A perturbation is applied to a feature VECTOR, but every rule here mirrors a
real change to a real MQTT packet, so a vector that passes is_protocol_valid()
corresponds to traffic a broker would accept. The live Mosquitto replay
(mosquitto_testbed/) is the physical confirmation of that correspondence.
"""
import numpy as np

import config

# Encoded feature order (from data_loader.encode on the full file).
FEATURES = [
    "tcp.flags", "tcp.time_delta", "tcp.len", "mqtt.conack.flags", "mqtt.conack.val",
    "mqtt.conflag.cleansess", "mqtt.conflag.passwd", "mqtt.conflag.uname", "mqtt.conflags",
    "mqtt.dupflag", "mqtt.hdrflags", "mqtt.kalive", "mqtt.len", "mqtt.msgid",
    "mqtt.msgtype", "mqtt.proto_len", "mqtt.protoname", "mqtt.qos", "mqtt.retain", "mqtt.ver",
]
IDX = {f: i for i, f in enumerate(FEATURES)}

# Packet type numbers
CONNECT, PUBLISH = 1, 3

# WHICH PACKETS THE ATTACKER CAN RESHAPE (added 16 Nov 2026 after
# o2_validity_audit.py showed many "evasions" were not realistic packets).
# MQTT 3.1.1 packet types a CLIENT sends: CONNECT 1, PUBLISH 3, PUBREL 6,
# SUBSCRIBE 8, UNSUBSCRIBE 10, PINGREQ 12, DISCONNECT 14. Every other row is
# out of the attacker's hands and is never perturbed:
#   - type 0 = bare TCP, no MQTT packet in the row. The dataset has no IP/port
#     fields, so we cannot tell whose TCP packet it is; we leave it alone.
#   - CONNACK 2, PUBACK 4, PUBREC 5, PUBCOMP 7, SUBACK 9, UNSUBACK 11,
#     PINGRESP 13 = replies. In MQTTset the clients only publish, so these come
#     from the broker.
ATTACKER_SENT = {1, 3, 6, 8, 10, 12, 14}
# Of those, only these have a variable length that can be padded (longer
# client id / topic / payload). The others have a fixed length in the standard.
PADDABLE = {1, 3, 8, 10}


def in_attack_scope(x):
    """True if this row is an MQTT packet the attacker sends (so may reshape)."""
    return int(round(x[IDX["mqtt.msgtype"]])) in ATTACKER_SENT

# Realistic bounds, measured from the data (see the inline note in phase2_attacks).
TIME_DELTA_CAP = 60.0      # seconds; the largest legitimate inter-packet gap observed
MQTT_LEN_CAP = 692.0       # bytes; largest mqtt.len observed, so padding stays in-range
MQTT_OVERHEAD = 2          # fixed-header + length byte: tcp.len >= mqtt.len + 2


def mutable_fields(constraint_set):
    """Names of the fields the attacker may change under each constraint set."""
    report = ["tcp.time_delta", "mqtt.len", "mqtt.kalive"]  # tcp.len moves with mqtt.len
    if constraint_set == "report":
        return report
    if constraint_set == "extended":
        return report + ["mqtt.qos", "mqtt.retain"]
    raise ValueError(constraint_set)


def _low_nibble_for_publish(dup, qos, retain):
    """PUBLISH header low 4 bits = DUP<<3 | QoS<<1 | RETAIN (MQTT 3.1.1 §3.3.1)."""
    return 8 * int(dup) + 2 * int(qos) + int(retain)


def apply_perturbation(x, changes):
    """
    Return a new feature vector with `changes` applied and every DEPENDENT field
    updated so the packet stays internally consistent. `changes` maps a mutable
    field name to its new value. Raises nothing; clipping and dependencies are
    enforced here, validity is checked separately by is_protocol_valid.
    """
    v = x.copy().astype(float)
    mtype = int(round(v[IDX["mqtt.msgtype"]]))

    # --- timing: may only INCREASE (attacker can add delay, not remove it) ---
    if "tcp.time_delta" in changes:
        nd = max(v[IDX["tcp.time_delta"]], min(changes["tcp.time_delta"], TIME_DELTA_CAP))
        v[IDX["tcp.time_delta"]] = nd

    # --- padding: mqtt.len may only INCREASE; tcp.len moves with it (dependent) ---
    if "mqtt.len" in changes and mtype in PADDABLE:
        old_len = v[IDX["mqtt.len"]]
        new_len = min(max(changes["mqtt.len"], old_len), MQTT_LEN_CAP)
        v[IDX["tcp.len"]] = v[IDX["tcp.len"]] + (new_len - old_len)
        v[IDX["mqtt.len"]] = new_len

    # --- keep-alive: only meaningful in CONNECT packets ---
    if "mqtt.kalive" in changes and mtype == CONNECT:
        v[IDX["mqtt.kalive"]] = float(np.clip(changes["mqtt.kalive"], 0, 65535))

    # --- extended levers: QoS / RETAIN, with dependent msgid + hdrflags ---
    if mtype == PUBLISH:
        if "mqtt.qos" in changes:
            v[IDX["mqtt.qos"]] = float(int(changes["mqtt.qos"]) & 1)
        if "mqtt.retain" in changes:
            v[IDX["mqtt.retain"]] = float(int(changes["mqtt.retain"]) & 1)
        qos = int(v[IDX["mqtt.qos"]])
        # message ID present (non-zero) iff QoS > 0 (MQTT 3.1.1 §2.3.1)
        if qos == 0:
            v[IDX["mqtt.msgid"]] = 0.0
        elif v[IDX["mqtt.msgid"]] <= 0:
            v[IDX["mqtt.msgid"]] = 1.0
        # DUP = 1 only if QoS > 0
        if qos == 0:
            v[IDX["mqtt.dupflag"]] = 0.0
        # header flags follow dup/qos/retain
        v[IDX["mqtt.hdrflags"]] = 16 * PUBLISH + _low_nibble_for_publish(
            v[IDX["mqtt.dupflag"]], qos, v[IDX["mqtt.retain"]])
    return v


# Fields an attacker must never change: doing so makes a different or invalid packet.
IMMUTABLE = ["mqtt.msgtype", "mqtt.protoname", "mqtt.proto_len", "mqtt.ver",
             "mqtt.conflags", "mqtt.conack.flags", "mqtt.conack.val", "tcp.flags",
             "mqtt.conflag.cleansess", "mqtt.conflag.passwd", "mqtt.conflag.uname"]


def is_protocol_valid(x_orig, x_new, attack_class=None):
    """
    True if x_new is a valid MQTT 3.1.1 packet reachable from x_orig by an allowed
    change. Mirrors the structural rules measured in constraint_checks.py.
    attack_class (e.g. "slowite") switches on rules that keep that attack working.
    """
    def g(v, f):
        return v[IDX[f]]
    mtype0 = int(round(g(x_orig, "mqtt.msgtype")))
    # rows the attacker does not send may not change at all
    if mtype0 not in ATTACKER_SENT and np.any(np.abs(x_new - x_orig) > 1e-9):
        return False
    # fixed-length packet types cannot be padded
    if mtype0 not in PADDABLE and abs(g(x_new, "mqtt.len") - g(x_orig, "mqtt.len")) > 1e-9:
        return False
    # SlowITe works by holding connections open with a long keep-alive
    # (constraint table, row 11): changing it stops the attack.
    if attack_class == "slowite" and abs(g(x_new, "mqtt.kalive") - g(x_orig, "mqtt.kalive")) > 1e-9:
        return False
    # immutable fields unchanged
    for f in IMMUTABLE:
        if abs(g(x_new, f) - g(x_orig, f)) > 1e-6:
            return False
    mtype = int(round(g(x_new, "mqtt.msgtype")))
    # timing only increased; padding only increased
    if g(x_new, "tcp.time_delta") < g(x_orig, "tcp.time_delta") - 1e-9:
        return False
    if g(x_new, "mqtt.len") < g(x_orig, "mqtt.len") - 1e-9:
        return False
    # tcp.len must still hold at least the MQTT bytes
    if mtype != 0 and g(x_new, "tcp.len") < g(x_new, "mqtt.len") + MQTT_OVERHEAD - 1e-9:
        return False
    if mtype == PUBLISH:
        qos = int(round(g(x_new, "mqtt.qos")))
        if qos not in (0, 1, 2):
            return False
        # msgid present iff qos>0
        if (g(x_new, "mqtt.msgid") > 0) != (qos > 0):
            return False
        # dup only if qos>0
        if g(x_new, "mqtt.dupflag") == 1 and qos == 0:
            return False
        # header low nibble consistent
        expect = 16 * PUBLISH + _low_nibble_for_publish(
            g(x_new, "mqtt.dupflag"), qos, g(x_new, "mqtt.retain"))
        if abs(g(x_new, "mqtt.hdrflags") - expect) > 1e-6:
            return False
    elif mtype != 0:
        # non-PUBLISH: hdrflags unchanged (we never perturb those bits)
        if abs(g(x_new, "mqtt.hdrflags") - g(x_orig, "mqtt.hdrflags")) > 1e-6:
            return False
    return True


def n_changed_features(x_orig, x_new):
    return int(np.sum(np.abs(x_new - x_orig) > 1e-6))
