# O2–O4 Findings — Attacks, Defence, Trade-off

> **⚠️ SUPERSEDED — DO NOT QUOTE THE O2–O4 NUMBERS BELOW (16 Nov 2026).**
> `src/o2_validity_audit.py` showed that most evasions in this run changed rows
> an attacker cannot reshape (bare TCP rows, broker replies, fixed-length
> packets). The attack rules in `src/constraints.py` were corrected on 16 Nov;
> the corrected run is being confirmed on the Mac and this document will be
> rewritten from it.


**Source:** `src/phase2_attacks.py`, `src/phase3_defence.py`,
`src/phase4_tradeoff.py`, run 15 Nov 2026 in the cloud session on Rasheed's
uploaded MQTTset copies (verified identical to his Mac copies in Phase 1).
Fixed seed 42. **Confirmed on Rasheed's Mac on 15 Nov 2026** — tables in
`mac_run_20261115/`. O2 and O4 classification numbers are identical; the one O3
difference is RF/report adaptive ASR (Mac 2.57%, cloud 2.55%). Latency below is
the Mac measurement.

Reproduce: `python3 src/run_phase2to4.py`. Read `O2_O4_DESIGN.md` first for how
each number is produced. All attacks target the models trained on **Variant B**
(the de-duplicated, leak-free split from Phase 1).

---

## Headline

1. **A constrained, realistic attacker breaks the neural network but barely
   dents the tree ensembles.** Under the report's own constraint set (timing +
   padding + keep-alive only), mean attack success over the five attack classes
   is **Random Forest 4.9%, XGBoost 29.3%, MLP 75.2%**.
2. **Adding QoS/retain to the attacker's toolkit barely changes this.** The
   detectors do not rely on a single shortcut; they use several signals, so the
   "extended" attack is within ~1 point of the "report" attack everywhere. This
   *tempers* the Phase 1 hypothesis that the QoS shortcut alone would break them.
3. **Adversarial training is cheap and highly effective.** After it, a *fresh*
   (adaptive) attack succeeds on **≤0.2%** of XGBoost attacks, **0.02–2.6%** of
   Random Forest attacks (extended / report set) and **~7%** of MLP attacks,
   while clean macro F1 stays within ±0.001 or rises.
4. **For deployment, XGBoost wins:** best clean F1 (0.871), near-perfect
   robustness after defence (99.85%), 1 MB, 0.10 ms/packet (Mac).

---

## O2 — Attack success rate (share of attacks disguised as legitimate)

Per attack class, "report" constraint set (timing/padding/keep-alive only):

| Class | Random Forest | XGBoost | MLP |
|---|---|---|---|
| dos | 0.0% | 0.8% | 73.2% |
| flood ⚠️ | 3.8% | 12.8% | 20.2% |
| bruteforce | 0.2% | 23.5% | 100.0% |
| malformed | 20.3% | 69.0% | 98.8% |
| slowite | 0.0% | 40.4% | 83.9% |
| **mean** | **4.9%** | **29.3%** | **75.2%** |

"extended" set (also allowing QoS/retain, with dependent fields updated) gives
means of RF 5.0%, XGBoost 29.4%, MLP 75.8% — essentially unchanged.

⚠️ `flood` has very few source records (78–79), so its rate is noisy; reported
but not relied upon, consistent with the Phase 1 reliability rule.

**Reading it:**
- **The MLP is fragile.** It is flipped by changing a *single* field (mean
  fields changed ≈ 1.0). A small, protocol-valid timing or padding change moves
  it across its decision boundary. This is the clearest evidence in the project
  for Prof. Yamani's overfitting concern — but located in the *neural network*,
  not the dataset.
- **Random Forest is the most robust**, then XGBoost. Tree ensembles make many
  independent splits, so one constrained change rarely flips all of them.
- **`dos` is nearly impossible to evade** on the tree models, because the
  detector keys on payload length (DoS packets are large, mean 169 bytes vs 11
  for normal) and the attacker can only *add* padding, not remove it. "A
  realistic attacker cannot evade" is itself a useful result (panel Q1/scope).
- **`malformed` and `slowite` are the soft spots** even for trees. `malformed`
  breaks the protocol by design, so it is a special case (handle separately).

Attack cost: the search needed ~30–120 model queries per packet and changed
1–3 fields — cheap, which makes the MLP's fragility more serious.

## O3 — Defence (adversarial training) under adaptive re-attack

The successful O2 samples are split in half; one half is added to training
(labelled with their true attack class), the other half held out. Then a
**fresh** attack is run against the retrained model.

| Model | Constraint set | Clean macro F1: undefended → defended | Adaptive re-attack ASR |
|---|---|---|---|
| Random Forest | report | 0.8559 → 0.8564 | **2.57%** (cloud 2.55%) |
| Random Forest | extended | 0.8559 → 0.8572 | **0.02%** |
| XGBoost | report | 0.8673 → 0.8667 | **0.18%** |
| XGBoost | extended | 0.8673 → 0.8705 | **0.12%** |
| MLP | report | 0.8030 → 0.8069 | **6.53%** |
| MLP | extended | 0.8030 → 0.8151 | **7.88%** |

- Adaptive attack success collapses: XGBoost from 29.3% to ~0.2%, the MLP from
  75% to ~7%. Random Forest on the report set falls less, from 4.9% to 2.6%
  (it was already hard to attack); on the extended set it falls to 0.02%. The held-out *old* samples also stop working (static ASR ≤4%).
- **Clean accuracy is not sacrificed** — it is flat to slightly higher. This is
  the opposite of the usual "adversarial training costs clean accuracy" worry
  (panel asks about this directly); report it honestly, it is a good result.

**Secondary defence — feature hardening (dropping `mqtt.qos`, `mqtt.msgid`,
`mqtt.hdrflags`): it does not help here.** Adaptive ASR with hardening is
*higher* than adversarial training alone in five of the six model/set pairs
(e.g. XGBoost report 5.05% vs 0.18%; RF report 9.42% vs 2.57%). The one
exception is MLP/extended, where hardening is lower (3.37% vs 7.88%). This is consistent with O2: the attacker was not
mainly exploiting those fields, so removing them buys no robustness and costs a
little accuracy. An honest negative result for the secondary mechanism.

## O4 — Robustness vs accuracy vs cost

Robustness = 100 − adaptive attack success rate (extended set). Latency and size
measured on Rasheed's Mac (15 Nov 2026, defended models); the cloud machine was
slower (RF ~5 ms, XGBoost 0.26 ms, MLP 0.32 ms).

| Model | Clean F1 (base→def) | Robustness (base→def) | Latency/packet | Size |
|---|---|---|---|---|
| Random Forest | 0.856 → 0.857 | 95.1% → **99.98%** | 3.28 ms | 42 MB |
| XGBoost | 0.867 → **0.871** | 70.4% → **99.85%** | **0.10 ms** | **1.1 MB** |
| MLP | 0.803 → 0.815 | 24.3% → 92.3% | 0.17 ms | **0.12 MB** |

Figure: `results/phase1/figures/o4_tradeoff.png` — every model moves right
(more robust) with no drop in height (clean F1).

**Deployment recommendation:** **XGBoost, adversarially trained.** It has the
best clean accuracy, near-complete robustness after defence, is small enough for
a gateway (1 MB) and fast (0.10 ms/packet). Random Forest is equally robust but
about 40× larger and 30× slower. The MLP is the smallest but the least robust even
after defence, so it is not recommended despite its size.

## Answers to the research questions

- **RQ1 (does detection survive an aware adversary?):** It depends entirely on
  the model. Tree ensembles largely survive a constrained attacker; the neural
  network does not (75% evasion). So the blanket "97–99% accuracy means solved"
  claim is unsafe for deep-learning detectors.
- **RQ2 (what perturbations preserve validity and function?):** timing increase,
  payload padding, keep-alive, and (extended) QoS/retain with dependent fields —
  all checked against MQTT 3.1.1 in `constraints.py` and confirmable on the
  Mosquitto testbed.
- **RQ3 (which defence works?):** adversarial training, decisively, under
  adaptive re-attack, at no clean-accuracy cost. Feature hardening does not add
  value here.
- **RQ4 (trade-off?):** adversarial training buys large robustness for
  near-zero accuracy/latency/size cost; XGBoost is the best operating point.

## Limits (state these plainly)

- Validity ≠ effect. The code and testbed prove the perturbed packets are legal
  MQTT; they do not prove a slowed/padded DoS still overwhelms the broker. Load
  testing is future work (report already says so).
- The attacker may only *increase* padding (cannot shrink a real payload). A
  DoS able to use smaller payloads might evade more; a testbed question.
- MQTTset feature space only; MQTT-IoT-IDS2020 cross-dataset work is separate.
- `flood` per-class rates are noisy (small n).
