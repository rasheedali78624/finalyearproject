# Phase 2 (O2) — Feature Constraint Table, draft v1 (5 Nov 2026)

**What this is:** for each of the 20 model features, can an attacker change it
without breaking the MQTT protocol or the attack itself, and under what rule?

**Sources:**
- the MQTT 3.1.1 specification (OASIS standard, 2014);
- rule checks and value ranges measured on MQTTset by `src/constraint_checks.py`
  (cloud run on verified data copies, tables in
  `docs/phase2/evidence_cloud_20261105/`; re-run on the Mac to confirm).

**Status:** draft for review with Dr. Bryan. Rows marked **TESTBED** need
checking on a live Mosquitto broker before they are final.

## Categories

| Category | Meaning |
|---|---|
| **Mutable** | The attacker sets it freely within the valid range |
| **Mutable (bounded)** | The attacker can change it, but only one way or within limits, or the attack stops working |
| **Dependent** | Calculated from other fields; it changes only when they do, by the rule given |
| **Immutable** | Cannot change without breaking the protocol or changing what the packet does |
| **Not attacker-controlled** | Sent by the broker, not by the attacker |

## The table

"Data check" = share of rows obeying the rule in MQTTset.

| # | Feature | In which packets | Values in data | Category | Rule | Data check |
|---|---|---|---|---|---|---|
| 1 | `mqtt.msgtype` | all MQTT | 0 (absent), 1–14 | **Immutable** | Defines what the packet is. Changing it changes the action. | – |
| 2 | `mqtt.hdrflags` | all MQTT | 14 values | **Dependent** | = 16·msgtype + (PUBLISH: 8·dup + 2·qos + retain; other types: fixed bits) | 100% (both rules) |
| 3 | `mqtt.qos` | PUBLISH | 0, 1 (2 allowed) | **Mutable** | {0, 1, 2}, the sender's choice. **TESTBED:** does the attack still work at the new QoS? | – |
| 4 | `mqtt.msgid` | PUBLISH (QoS>0), SUBSCRIBE, acks | 0–10,000 | **Dependent** (presence) + **Mutable** (value) | Present ⇔ QoS > 0 on PUBLISH; value 1–65,535 freely chosen | 99.98% (39 exceptions, all `malformed`) |
| 5 | `mqtt.dupflag` | PUBLISH | 0, 1 | **Mutable (bounded)** | DUP = 1 only if QoS > 0 | 100% |
| 6 | `mqtt.retain` | PUBLISH | 0, 1 | **Mutable** | 0/1. Side effect: the broker stores the message for new subscribers | – |
| 7 | `mqtt.len` | all MQTT | 0–692 | **Mutable (bounded)** | Remaining length. The attacker can lengthen or shorten the topic or payload, but not below the minimum valid size for the packet type | – |
| 8 | `tcp.len` | all | 0–32,768 | **Dependent** | Bytes of MQTT data in the TCP segment. Only 60.20% of MQTT rows have tcp.len = mqtt.len + 2; segments often hold several MQTT packets or part of one. **TESTBED:** measure the real rule | 88.05% have tcp.len ≥ mqtt.len + 2 |
| 9 | `tcp.time_delta` | all | −0.000002 to 60.0 s | **Mutable (bounded)** | The attacker can **add** delay, not remove it. Slowing down weakens flooding attacks (dos, flood) | 1 negative value (capture artefact) |
| 10 | `tcp.flags` | all | 8 values (ACK, PSH+ACK, SYN, SYN+ACK, FIN+ACK, RST…) | **Immutable** (except PSH) | SYN/FIN/RST/ACK follow the TCP connection state. PSH (0x18 vs 0x10) on data segments is the sender's choice | – |
| 11 | `mqtt.kalive` | CONNECT | 0, 1, 2, 3, 60, 234, 65,535 | **Mutable** (**Immutable for `slowite`**) | 0–65,535 seconds, the client's choice. SlowITe needs a long keep-alive to hold connections open | All 1,016 `slowite` CONNECTs use 65,535 |
| 12 | `mqtt.conflag.cleansess` | CONNECT | 0, 1 | **Mutable** | 0/1, the client's choice | – |
| 13 | `mqtt.conflag.uname` | CONNECT | 0, 1 | **Mutable** (**Immutable for `bruteforce`** = 1) | Sending credentials is the bruteforce attack. Other attacks can omit them only if the broker allows anonymous login (**TESTBED**) | – |
| 14 | `mqtt.conflag.passwd` | CONNECT | 0, 1 | Same as uname | Password flag = 1 only if username flag = 1 | 100% |
| 15 | `mqtt.conflags` | CONNECT | absent, 2, 130, 194 | **Dependent** | = 128·uname + 64·passwd + 2·cleansess (will flags constant 0 in this data). *Report said immutable; correct to dependent.* | 100% |
| 16 | `mqtt.protoname` | CONNECT | absent, MQTT | **Immutable** | Must be "MQTT" for version 3.1.1 | 100% |
| 17 | `mqtt.proto_len` | CONNECT | 0, 4 | **Immutable** | = 4 (length of "MQTT") | 100% |
| 18 | `mqtt.ver` | CONNECT | 0, 4 | **Immutable** | 4 = MQTT 3.1.1. Other versions change the protocol and are out of scope | 100% |
| 19 | `mqtt.conack.flags` | CONNACK | absent, 0 | **Not attacker-controlled** | Sent by the broker | 100% only in CONNACK |
| 20 | `mqtt.conack.val` | CONNACK | 0, 5 | **Not attacker-controlled** | Broker's answer: 0 = accepted, 5 = not authorised | 100% only in CONNACK |

**Structural rule (100% of rows):** fields belonging to one packet type are
absent or zero in all other types. A perturbation must never put, say, a
keep-alive into a PUBLISH packet.

## Summary

| Category | Features |
|---|---|
| Mutable | `mqtt.qos`, `mqtt.retain`, `mqtt.msgid` (value), `mqtt.kalive`¹, `mqtt.conflag.cleansess`, `mqtt.conflag.uname`², `mqtt.conflag.passwd`² |
| Mutable (bounded) | `tcp.time_delta` (increase only), `mqtt.len` (≥ minimum), `mqtt.dupflag` (needs QoS > 0), PSH bit of `tcp.flags` |
| Dependent | `mqtt.hdrflags`, `mqtt.conflags`, `mqtt.msgid` (presence), `tcp.len` |
| Immutable | `mqtt.msgtype`, `mqtt.protoname`, `mqtt.proto_len`, `mqtt.ver`, `tcp.flags` (except PSH) |
| Not attacker-controlled | `mqtt.conack.flags`, `mqtt.conack.val` |

¹ fixed for `slowite`. ² fixed at 1 for `bruteforce`.

## What each attack can change (from packet types in the data)

| Attack | Packets it sends (MQTTset rows) | Must keep | Can change |
|---|---|---|---|
| `dos` | PUBLISH 54,431 (all QoS 1); PUBACK 38,841; bare TCP 36,906 | Message type and a high message rate | **QoS** (then msgid and hdrflags follow), retain, payload length, a little delay |
| `flood` | PUBLISH 295 (QoS 0); bare TCP 310 | Heavy publishing | Payload length (bounded), retain, QoS, delay (bounded) |
| `bruteforce` | CONNECT 1,430 / CONNACK 1,430 (keep-alive 60); bare TCP 11,580 | uname = passwd = 1 | Keep-alive, clean session, delay |
| `slowite` | CONNECT 1,016 / CONNACK 1,016 (keep-alive 65,535); bare TCP 7,170 | Long keep-alive | Clean session, credentials (if anonymous login is allowed), delay |
| `malformed` | Mixed; breaks protocol rules on purpose | Its malformation | **Handle separately:** "protocol-valid" does not apply (see the direction review, change 3) |

## Corrections to the submitted report's constraint set

- `mqtt.conflags`: **immutable → dependent**.
- `tcp.len`: **mutable → dependent**. The `mqtt.len ↔ tcp.len` link is real, but
  it is not the simple fixed rule the report assumed.
- **Add as attacker-mutable:** `mqtt.qos`, `mqtt.retain`, `mqtt.dupflag`,
  `mqtt.msgid` value, `mqtt.conflag.cleansess`.
- **Add as not attacker-controlled:** `mqtt.conack.flags`, `mqtt.conack.val`.
- **Remove:** `mqtt.msg`, which is dropped from the features.

## Open questions for the testbed

1. Does a QoS-0 DoS still overload Mosquitto? This decides whether the
   "QoS 0 evasion" keeps the attack working.
2. What `tcp.len` does a single MQTT packet of a given `mqtt.len` actually
   produce, and when do packets get merged into one segment?
3. Does Mosquitto, in the MQTTset set-up, allow anonymous login? If not,
   uname and passwd are fixed at 1 for every attack.
4. Which value range of `tcp.time_delta` still lets each flooding attack
   overload the broker?
