# Project Direction Review — after Phase 1 (5 Nov 2026)

**Purpose:** decide whether the study design or the dataset needs to change,
based on everything measured so far.

**Evidence:** Phase 1 results (Mac run), plus two new scripts run in the cloud
on the same verified data copies: `src/mqtt_only_analysis.py` and
`src/constraint_checks.py`. Re-run both on the Mac (about 1 minute each) before
quoting their numbers. Tables are archived in `docs/phase2/evidence_cloud_20261105/`.

**Status: recommendations for discussion with Dr. Bryan, not decisions.**

---

## 1. Verdict in one paragraph

**Keep the title, the four objectives, and MQTTset as the primary dataset.**
Change **which packets O2–O4 are evaluated on**: use only packets that carry
an MQTT layer. Also change **how the core argument is framed**. The data does
not support "published accuracy is fake". It supports a sharper claim: *the
detectors are genuinely accurate on MQTT packets, but they rely on a few
shortcut features that an attacker can change while keeping the traffic valid
MQTT.* That is precisely what O2 tests, so the project gets more focused, not
bigger.

## 2. What the evidence now says

### 2a. The difficulty in MQTTset comes from bare TCP packets

| Population | Rows | Rows in a label conflict | Accuracy ceiling | XGBoost macro F1 (de-duplicated, grouped split) |
|---|---|---|---|---|
| All rows (Phase 1, Variant B) | 330,926 | 34.89% | 93.27% | 0.8673 |
| **MQTT packets only** | **206,975** | **0.06%** | **99.98%** | **0.9792** |

On MQTT packets only, Random Forest scores 0.9781 and the MLP 0.8898.
Accuracy is 99.82–99.84% for the tree models, with false-positive rate 0.0006
(`mqtt_only_models`).

- 123,951 rows (37.46%) are bare TCP packets (ACKs, handshakes) with no MQTT
  content, labelled by capture file. They cause nearly all label conflicts.
- Without them, the honest, leak-free score is **high**: macro F1 0.98 on a
  de-duplicated split where no packet shape is on both sides.

**What this means:** the high published scores are not simply an artefact of
leakage. Leakage is real (34.37% of the published test set is answered from
memory), but on MQTT packets a detector really can separate these attacks. The
interesting question is therefore **why** it can, and whether an attacker can
take that away. That is O2.

### 2b. The detectors can rely on shortcuts (from `constraint_checks`)

| Shortcut in the data | Evidence | Can an attacker change it? |
|---|---|---|
| **DoS publishes with QoS 1; normal traffic always QoS 0** | All 54,431 `dos` PUBLISH packets have QoS 1; all 101,966 `legitimate` PUBLISH packets have QoS 0 | **Yes.** QoS is the sender's choice. Whether DoS still works at QoS 0 must be tested on a broker. |
| **Message ID present ⇔ QoS > 0** | Holds for 99.98% of PUBLISH rows | Follows from QoS: switching to QoS 0 removes the message ID too. This explains why `mqtt.msgid` is XGBoost's top feature. |
| **Normal traffic contains no CONNECT packets at all** | 0 `legitimate` CONNECT rows; every CONNECT row in the data is an attack | No for bruteforce, which must connect. But a real deployment has normal devices connecting, so the measured false-positive rate is optimistic. **Dataset limitation.** |
| **SlowITe always uses keep-alive 65535** | All 1,016 `slowite` CONNECT rows | No: the long keep-alive is how SlowITe works. |
| `slowite` payload written as `0.0` | Step 2 | Removed by dropping `mqtt.msg`. |

**Hypothesis for O2, to test, not yet shown:** XGBoost's strong DoS detection
depends largely on QoS and message ID. A DoS attacker who switches to QoS 0,
keeping valid MQTT, will evade much of it.

### 2c. The protocol rules hold in the data, so they can be enforced

Every structural MQTT rule checked holds on **100%** of rows, except two:
- **Message ID ⇔ QoS: 39 exceptions, all `malformed`.** Malformed packets break
  the protocol on purpose.
- **`tcp.len` and `mqtt.len`:** they are related by a simple +2 in only 60.20%
  of MQTT rows. TCP segments often carry several MQTT packets, or part of one.

Details are in `docs/phase2/CONSTRAINT_TABLE.md`.

## 3. Recommended changes

| # | Change | Why | Cost / risk |
|---|---|---|---|
| **1** | **O2–O4 use MQTT packets only**, de-duplicated with the grouped split ("MQTT-only Variant B"). Keep the all-rows Phase 1 results as the benchmark-quality finding. | Bare TCP packets carry no MQTT fields to perturb and are mostly label noise. The clean baseline (macro F1 0.98) makes any drop under attack measurable and meaningful. | The detector no longer sees TCP-only traffic. `slowite` shrinks to 743 unique rows (222 test). `flood` has only 71 test rows, so its per-class result stays unreliable. |
| **2** | **Reframe the argument:** from "published accuracy is inflated" to "accuracy is real on MQTT packets but rests on attacker-controllable shortcuts". Leakage and label noise remain Phase 1 findings. | This is what the data shows. Overclaiming inflation would be wrong for MQTT-only data. | The report's introduction needs rewording (see §5). |
| **3** | **Treat `malformed` separately in O2.** | Malformed traffic is protocol-invalid by design, so "keep the packet protocol-valid" cannot apply to it. The constraint becomes "stay as malformed as the original". | Simplest option: exclude it from evasion experiments and say why. |
| **4** | **Attack XGBoost first (primary), Random Forest second.** Use one black-box, constraint-respecting search method that works for all three models. | XGBoost is the best model and the realistic choice to deploy. One attack method keeps the scope manageable (Prof. Yamani's "ambitious" point). | Gradient-based attacks would only work on the MLP, so skip them. |
| **5** | **A Mosquitto testbed is needed for three questions:** (a) does a DoS still hurt the broker at QoS 0? (b) what are the real `tcp.len`/`mqtt.len` rules? (c) does the broker accept each perturbed packet? | These cannot be answered from the CSV. | Setup time. It runs locally on the Mac. |

**Optional, only if time allows after O3:** run the Task 1 and Step 2
analysis (no new models) on MQTT-IoT-IDS2020's `packet_features`. Most papers
in the reading list use that dataset (`papers/PAPER_SCAN.md`), so showing
whether the same problems appear there would strengthen the contribution. Ask
Dr. Bryan before starting; it adds scope.

## 4. What should NOT change

- Macro F1 as the headline; per-class results; `flood` flagged unreliable.
- No SMOTE or synthetic packets.
- Fixed seed 42; every number from code that ran; Mac runs are official.
- Variant A (the published split) kept, for comparability with the literature.
- `mqtt.msg` dropped.

## 5. Corrections needed in the submitted report

| Report says | Evidence says |
|---|---|
| 33 features | 20 usable: 12 are constant, and `mqtt.msg` is dropped |
| 7 text columns | 6 text feature columns (the 7th is the label) |
| ~22.6% train/test overlap | 66.91% (raw columns), 69.59% (20 features) |
| `mqtt.conflags` is immutable | It is **derived**: 128·uname + 64·passwd + 2·cleansess (holds on 100% of CONNECT rows). It changes whenever those flag bits change. |
| `tcp.len` is mutable | It is **dependent**: set by the MQTT bytes in the TCP segment. The rule must be measured on the testbed. |
| (not listed) | `mqtt.qos`, `mqtt.retain`, `mqtt.dupflag`, `mqtt.msgid`, `mqtt.conflag.cleansess` are attacker-controllable. `mqtt.conack.*` are sent by the broker and are not attacker-controllable. |
| `mqtt.msg` in the feature space | Dropped; it leaves the constraint set |

## 6. Revised plan

| When | What |
|---|---|
| This week | Dr. Bryan: Phase 1 results, the four Phase 1 decisions, **plus change 1 (MQTT-only) and change 2 (framing)** |
| Weeks of 9 and 16 Nov | Finalise the constraint table (`docs/phase2/CONSTRAINT_TABLE.md`). Set up Mosquitto on the Mac. Answer the three testbed questions. |
| Weeks of 23 and 30 Nov | First attack: QoS-0 DoS against XGBoost on MQTT-only Variant B. Then the general constraint-respecting search. |
| December | Measure detection drop per attack and per model. Draft the O2 results. |
| End Dec / Jan | Show Phase 1 complete and O2 results. O3 (adversarial training) next. |

## 7. Uncertain

- The MQTT-only and constraint numbers are from the cloud run; confirm on the Mac.
- Whether DoS at QoS 0 still overloads the broker: **not measured, needs the testbed.**
- Whether shortcut features really drive the detectors' decisions: feature
  importance suggests it for `mqtt.msgid`, but that is a hypothesis until O2
  tests it.
- The dataset has no IP or port fields, so it cannot tell client-to-broker
  packets from broker-to-client packets. Constraints use packet type as a
  stand-in (§ "not attacker-controlled" in the constraint table).
