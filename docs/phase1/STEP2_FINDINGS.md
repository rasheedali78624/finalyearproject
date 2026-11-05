# Phase 1 · Step 2 — Feature-Space Findings

**Source of every number:** `src/feature_space_analysis.py`, run on 5 Nov 2026
in the cloud session on Rasheed's own uploaded copies of the three MQTTset
files. The copies were checked first: `src/dedup_analysis.py` on them gave
output identical, line for line, to Rasheed's Mac run of 12:46.
**These numbers must still be confirmed by running the same script on the Mac.**
They are expected to match exactly.

**To reproduce:** `python3 src/feature_space_analysis.py` (about 45 seconds).

---

## 1. Encoding decisions

| Decision | Reason |
|---|---|
| Drop the 12 constant columns | They never vary, so they carry no information |
| **Drop `mqtt.msg`** | Payload text with 50,054 values. A model could memorise payloads, and an attacker controls them completely. **It also contains a class giveaway (§3).** Dropping it removes it from the O2 constraint set. |
| Hex columns (`tcp.flags`, `mqtt.conack.flags`, `mqtt.conflags`, `mqtt.hdrflags`) → integer | They are numbers written in base 16 |
| Plain `0` in those hex columns → −1 | Plain `0` means "field not in this packet"; `0x00000000` means "present, value 0". The two stay distinct. |
| `mqtt.protoname`: `0` → 0, `MQTT` → 1 | Only two values |
| All other columns → float | Already numeric; checked to contain no text |

**Result: 20 model features** (3 TCP, 17 MQTT). No column lost distinct
values in the conversion (table `encoding_report`).

## 2. The label-conflict hypothesis is confirmed

**Hypothesis (from Task 1):** the conflicting rows are packets with no MQTT
layer.

**Test:** count rows with no MQTT header (`mqtt.hdrflags` is a plain `0`).

| | Rows | With no MQTT header |
|---|---|---|
| In a label conflict | 115,447 | **115,324 (99.89%)** |
| Not in a conflict | 215,479 | 8,627 (4.0%) |
| All rows | 330,926 | 123,951 (37.46%) |

**Conclusion:** almost every label conflict is a bare TCP packet, such as an
ACK or a handshake, carrying no MQTT content. Such packets look the same
whichever capture they came from, but each takes the label of its capture
file. This is a property of how MQTTset was labelled (per capture, not per
packet), and it should be stated as a limitation of the dataset.

Share of each class that has no MQTT header:

| Class | No MQTT header |
|---|---|
| bruteforce | 79.86% |
| slowite | 77.92% |
| malformed | 66.53% |
| flood | 50.57% |
| legitimate | 36.70% |
| dos | 28.34% |

## 3. `mqtt.msg` contained a class giveaway

In the raw file, **every one of the 9,202 `slowite` rows, and no other row,
writes the payload as `0.0`**. All other classes write `0`. This is a
formatting artefact of how the dataset was produced, not attack behaviour. A
model reading `mqtt.msg` as text could identify `slowite` from it perfectly.

Evidence: once `mqtt.msg` is dropped, `slowite` goes from 0% label conflicts
(Task 1) to 47.52% (§4). The only thing that told those rows apart was the
artefact.

This is an extra, independent reason for dropping `mqtt.msg`, and one worth
reporting: a published model that used it could score highly on `slowite` for
the wrong reason.

## 4. Re-measured on the 20 model features

| Measure | Raw 33 columns (Task 1) | 20 model features |
|---|---|---|
| Unique feature vectors | 119,978 | 107,129 |
| Rows in a label conflict | 110,711 (33.45%) | 115,447 (34.89%) |
| **Unavoidable errors (error floor)** | 18,594 (5.62%) | **22,278 (6.73%)** |
| **Best possible accuracy** | 94.38% | **93.27%** |
| Variant A test rows also in train | 66,432 (66.91%) | **69,092 (69.59%)** |

Per class:

| Class | Unique rows | Duplicate % | In conflict % | Variant A leakage % |
|---|---|---|---|---|
| legitimate | 6,023 | **96.36** | 36.61 | **98.43** |
| dos | 90,988 | 30.13 | 28.19 | 31.20 |
| bruteforce | 4,372 | 69.85 | 60.06 | 78.63 |
| malformed | 4,744 | 56.57 | 43.75 | 72.48 |
| slowite | 2,580 | 71.96 | 47.52 | 76.89 |
| flood | 266 | 56.61 | 49.92 | 65.76 |

**What changed:** `legitimate` drops from 18,374 to 6,023 unique rows. Most of
its variety was payload content. With `mqtt.msg` gone, **98.43% of the
legitimate rows in the published test set have an exact copy in the training
set.**

## 5. Variant B (de-duplicated, grouped split)

One row per (feature vector, label): **108,973 rows**, split 70/30 so that no
feature vector appears on both sides.

| Class | Train | Test | Test share |
|---|---|---|---|
| dos | 63,690 | 27,298 | 30.00% |
| legitimate | 4,215 | 1,808 | 30.02% |
| malformed | 3,321 | 1,423 | 30.00% |
| bruteforce | 3,059 | 1,313 | 30.03% |
| slowite | 1,805 | 775 | 30.04% |
| flood | 186 | **80** | 30.08% |
| **Total** | **76,276** | **32,697** | 30.00% |

- Leakage check: **0** test rows have a feature vector that is in train.
- ⚠️ **`flood` has only 80 test rows in Variant B.** That is below the
  100-row reliability line, so its per-class scores in Variant B must be
  labelled as unreliable.
- Variant B is dominated by `dos` (about 83% of rows, *derived*). This is the
  natural shape of the de-duplicated data, not a fault of the split.

## Still uncertain

- These numbers come from the cloud run; confirm them on the Mac.
- Whether published 97–99% studies used `mqttdataset_reduced.csv` and kept
  `mqtt.msg`. If they kept it, the `slowite` artefact may have helped them.
