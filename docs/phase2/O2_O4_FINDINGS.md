# O2–O4 Findings — Attacks, Defence, Trade-off

**Source:** `src/phase2_attacks.py`, `src/phase3_defence.py`,
`src/phase4_tradeoff.py`, run on Rasheed's Mac on **16 Nov 2026** with the
corrected attack rules. Fixed seed 42. Tables: `mac_run_20261116/`.
Reproduce: `python3 src/run_phase2to4.py` (about 8 minutes), then
`python3 src/o2_validity_audit.py`.

All attacks target the models trained on **Variant B** (the de-duplicated,
leak-free split from Phase 1). Read `O2_O4_DESIGN.md` for how each number is
produced.

> **This replaces the 15 Nov version.** That version reported mean attack
> success of RF 4.9%, XGBoost 29.3%, MLP 75.2%. Those numbers are withdrawn:
> see "What was corrected" below. Do not quote them.

---

## What was corrected (16 Nov 2026)

`src/o2_validity_audit.py` sorted every successful evasion of the 15 Nov run by
the kind of packet it was. Of XGBoost's 1,443 evasions (report set), only 387
were MQTT packets an attacker sends; 820 had an impossible length (for example
"padding" a row with no MQTT packet in it), 223 were broker replies and 13 were
bare TCP rows. For the MLP, 1,098 of 3,929 were attacker-sent MQTT packets.

Three rules in `src/constraints.py` were then fixed:

1. **Scope.** Only MQTT packet types a client sends are attacked (CONNECT,
   PUBLISH, PUBREL, SUBSCRIBE, UNSUBSCRIBE, PINGREQ, DISCONNECT). Bare TCP rows
   and broker replies are never changed. Bare TCP rows are excluded because the
   dataset has no address fields, so the sender cannot be identified; this can
   understate the attacker but not overstate it.
2. **Padding** is allowed only on variable-length packet types.
3. **`tcp.len`** must move by exactly the padding added. The earlier absolute
   rule (`tcp.len ≥ mqtt.len + 2`) is broken by 11.95% of real MQTT rows and
   had silently blocked every change to them, including all 125 SlowITe
   CONNECT packets.

Also: SlowITe's keep-alive is now fixed (constraint table row 11), and the
attack table records `no_allowed_change` (0 for every class in this run, so
every evaluated packet was genuinely attacked).

**Audit of this run (16 Nov, Mac):** all 6,022 saved evasions across the three
models and two constraint sets are attacker-sent MQTT packets; 0 impossible
lengths, 0 broker replies, 0 bare TCP rows. The per-class counts equal the
`evasions` column of the attack table.

---

## Headline

1. **Outside the `malformed` class, a constrained attacker cannot evade the
   tree models.** Over dos, flood, bruteforce and slowite, XGBoost was evaded
   on 1 of 1,673 attacked packets and Random Forest on 2 of 1,673.
2. **`malformed` is the weak point for every model:** 51.22% evasion on Random
   Forest, 82.04% on XGBoost, 98.76% on the MLP.
3. **The MLP is broken by one field.** 97.50% of dos, 100% of bruteforce and
   100% of slowite packets evade it, with a mean of 1.0 fields changed and 5–9
   queries.
4. **Adversarial training closes the gap for XGBoost** (mean re-attack success
   16.48% → 0.39%) and most of it for the MLP (80.72% → 6.64%), but only
   partly for Random Forest (10.83% → 6.79%). Clean macro F1 changes by at most
   0.002.
5. **For deployment, XGBoost adversarially trained** is the best operating
   point: clean F1 0.8688, robustness 99.58%, 1.1 MB, 0.106 ms/packet (Mac).

---

## O2 — Attack success rate

Share of detected, attacker-sent packets of each class that the attack
disguised as legitimate. "Report" constraint set (timing, padding, keep-alive).

| Class | Packets attacked | Random Forest | XGBoost | MLP |
|---|---|---|---|---|
| dos | 1,200 (sampled from 16,243) | 0.00% | 0.00% | 97.50% |
| flood ⚠️ | 68 | 2.94% | 0.00% | 7.35% |
| bruteforce | 280 | 0.00% | 0.36% | 100.00% |
| malformed | 566–574 | 51.22% | 82.04% | 98.76% |
| slowite | 125 | 0.00% | 0.00% | 100.00% |
| **mean of 5 classes** | | **10.83%** | **16.48%** | **80.72%** |
| mean without malformed | | 0.73% | 0.09% | 76.21% |

"Extended" set (also QoS/retain): means RF 10.94%, XGBoost 16.48%, MLP 82.40%.
XGBoost's results are identical in both sets; the QoS/retain lever gave the
attacker nothing extra against it.

⚠️ `flood` has 68 attacker packets in the test set; its rate is noisy and is
reported but not relied upon.

**Reading it**

- **The two means tell different stories, so always give both.** The 5-class
  mean for the tree models is almost entirely the `malformed` class.
- **`malformed` needs separate treatment.** These packets break the protocol on
  purpose, so "keep the packet protocol-valid" does not strictly apply to them;
  the rules here only guarantee the attacker changed timing or padding and
  nothing else. The direction review (change 3) already recommended handling
  this class separately. One changed field is enough (mean fields changed 1.0).
- **dos, bruteforce and slowite are not evadable on the tree models** within
  this attacker's limits: the full budget of 120 queries was used on every
  packet without success.
- **The MLP's weakness is general**, not tied to one class.
- **Attack success is measured on packets the model detects.** Packets missed
  with no attack at all are counted in `missed_without_attack` (at most 8 per
  class here) and included in `end_to_end_miss_pct`.

**Scope of the claim.** In the test set, attacker-sent MQTT packets are 59.50%
of dos rows, 85.00% of flood, 21.33% of bruteforce, 40.34% of malformed and
16.13% of slowite. The rest are broker replies and bare TCP rows, which this
attack does not touch.

## O3 — Defence (adversarial training) under adaptive re-attack

The successful O2 samples are split in half; one half is added to training
with their true class, the other half is held out. A **fresh** attack is then
run against the retrained model.

| Model | Set | Clean macro F1: before → after | Mean attack success: before → after | End-to-end miss after |
|---|---|---|---|---|
| Random Forest | report | 0.8559 → 0.8568 | 10.83% → 6.79% | 6.79% |
| Random Forest | extended | 0.8559 → 0.8571 | 10.94% → 6.76% | 6.76% |
| XGBoost | report | 0.8673 → 0.8688 | 16.48% → 0.39% | 0.49% |
| XGBoost | extended | 0.8673 → 0.8688 | 16.48% → 0.42% | 0.52% |
| MLP | report | 0.8030 → 0.8032 | 80.72% → 6.64% | 6.84% |
| MLP | extended | 0.8030 → 0.8011 | 82.40% → 9.86% | 10.01% |

- **XGBoost benefits most:** a fresh attack succeeds on under half a percent.
- **Random Forest benefits least:** about 6.8% still gets through. Which class
  that is has not been broken down yet (it is in the run log, not the table).
- **Clean accuracy is essentially unchanged** (−0.0019 to +0.0015 macro F1).
- "End-to-end miss" also counts attack packets the retrained model misses with
  no attack at all, so a model cannot look robust simply by detecting less.

**Secondary defence — feature hardening** (dropping `mqtt.qos`, `mqtt.msgid`,
`mqtt.hdrflags`): **no consistent benefit.** Compared with adversarial training
alone it is worse for Random Forest (7.56% vs 6.79%), better for XGBoost (0.04%
vs 0.39%) at a cost of 0.0044 clean F1, much worse for the MLP on the report
set (26.57% vs 6.64%) and slightly better on the extended set (7.55% vs 9.86%)
at a cost of 0.0134 clean F1.

## O4 — Robustness vs accuracy vs cost

Robustness = 100 − mean adaptive attack success (extended set, up to 800
packets per class). Latency and size measured on Rasheed's Mac.

| Model | Clean F1 (base → def) | Robustness (base → def) | Latency/packet (def) | Size (def) |
|---|---|---|---|---|
| Random Forest | 0.8559 → 0.8571 | 89.06% → 93.24% | 3.246 ms | 42.2 MB |
| XGBoost | 0.8673 → **0.8688** | 83.52% → **99.58%** | **0.106 ms** | 1.1 MB |
| MLP | 0.8030 → 0.8011 | 17.60% → 90.14% | 0.162 ms | **0.12 MB** |

Figure: `results/phase1/figures/o4_tradeoff.png`.

**Deployment recommendation: XGBoost, adversarially trained.** Best clean
accuracy, highest robustness after defence, 1.1 MB, 0.106 ms per packet.
Random Forest is about 38× larger and 31× slower and stays less robust. The MLP
is the smallest but has the lowest accuracy and robustness.

## Answers to the research questions

- **RQ1 (does detection survive an aware adversary?):** For the tree models,
  yes for dos, flood, bruteforce and slowite, and no for `malformed`. For the
  neural network, no: about 81% mean evasion.
- **RQ2 (what perturbations preserve validity and function?):** added delay and
  payload padding on client-sent, variable-length packets; keep-alive on
  CONNECT (except SlowITe); QoS/retain with dependent fields. Encoded in
  `constraints.py`. Confirmation on a live broker is still to do.
- **RQ3 (which defence works?):** adversarial training, strongly for XGBoost
  and the MLP, partly for Random Forest, under adaptive re-attack and without
  clean-accuracy cost. Feature hardening adds no consistent value.
- **RQ4 (trade-off?):** adversarial training costs almost nothing in accuracy,
  latency or size; XGBoost is the best operating point.

## Limits (state these plainly)

- **Single run, one seed.** No confidence intervals on the attack or defence
  rates yet.
- **Validity ≠ effect.** The rules keep the perturbed packets legal MQTT; they
  do not show that a delayed or padded attack still harms the broker.
- **Not yet checked on a live broker** (Mosquitto testbed pending; its script
  needs rewriting to wait for the broker's reply).
- **Per-packet view.** Bare TCP rows and broker replies of an attack are not
  perturbed, and the detector may still flag the attack through them.
- The attacker may only *increase* delay and padding.
- MQTTset only; simulated traffic from eight sensors.
- `flood` rates rest on 68 packets.
