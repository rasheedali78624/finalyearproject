# O2–O4 Program Design — in plain words

This explains what the new code does and why, so you can defend every part of
it. No results are quoted here; the measured numbers live in
`O2_O4_FINDINGS.md` once the runs are in. Read this first, then that.

The code is in `src/`:

| File | Objective | What it does |
|---|---|---|
| `constraints.py` | shared | The rules: which fields an attacker may change, and what makes a packet still valid MQTT. |
| `phase2_attacks.py` | **O2** | The attack: tries to make the detector call an attack "legitimate". |
| `phase3_defence.py` | **O3** | The defence: adversarial training, then re-attacks the defended model. |
| `phase4_tradeoff.py` | **O4** | Joins it together: robustness vs accuracy vs cost. |
| `run_phase2to4.py` | all | Runs O2, O3, O4 in order with one command. |
| `mosquitto_testbed/` | O2 | Confirms the perturbed packets are valid on a real broker (you run this on your Mac). |

---

## 1. The idea in one picture

Your Phase 1 detector is good at spotting attacks **when the attacker is not
trying to hide**. O2 asks: what if the attacker *is* trying to hide, but can
only make changes that keep the packet a real, working MQTT packet? O3 then
builds a detector that resists that, and re-attacks it. O4 asks what the defence
costs.

```
   attack packet  ──O2──▶  can we change allowed fields so the
   (really is dos)          detector says "legitimate"?   ──▶ attack success rate
                                      │
                                      ▼
   O3: add the successful tricks to training, retrain  ──▶ defended detector
                                      │
                                      ▼
   O3: attacker tries again on the defended detector  ──▶ does the defence hold?
                                      │
                                      ▼
   O4: robustness gained vs clean accuracy and speed lost
```

## 2. `constraints.py` — the rulebook

Every adversarial change has to obey two things, both encoded here.

**What the attacker may change (the constraint set).** Two versions:

- **"report"** — exactly Table 3.5 of your report: only **timing**
  (`tcp.time_delta`, and it can only be *increased* — you can delay a packet,
  you cannot send it before it happened), **padding** (`mqtt.len`, increased,
  which drags `tcp.len` with it because they are linked), and **keep-alive**
  (`mqtt.kalive`, only meaningful in CONNECT packets).
- **"extended"** — the above *plus* `mqtt.qos` and `mqtt.retain`. Phase 1
  showed the detector leans on QoS (DoS always uses QoS 1, normal traffic QoS
  0). When QoS changes, the message ID and header-flag fields must change with
  it, or the packet is invalid; the code does that automatically.

Running both and comparing them is the point: the gap shows how much the
detector's robustness depends on fields your original report assumed the
attacker could not touch.

**What keeps a packet valid (`is_protocol_valid`).** After any change, the code
checks the MQTT 3.1.1 structural rules you already measured in Phase 2
groundwork: the message type is unchanged, the header flags still match the
QoS/retain bits, a message ID is present exactly when QoS > 0, `tcp.len` still
covers the MQTT bytes, and immutable fields are untouched. A perturbation that
fails any of these is thrown away, never counted. This is the code version of
"the broker would reject it".

## 3. `phase2_attacks.py` — the attack (O2)

**The attacker's knowledge (from your Table 3.4): grey-box.** It knows what the
features are and that a detector exists, but not the detector's internal
numbers. So it cannot do the gradient maths that image-attack papers use (this
is the point your panel notes make: there is no epsilon, there is a feasibility
set). Instead it **searches**: it proposes allowed, valid changes to a packet,
watches only the detector's yes/no decision, and keeps trying within a fixed
**query budget**. This is a "decision-based black-box search" and it is the
honest match to a grey-box attacker.

**For each attack packet the detector currently catches**, the attacker builds a
set of candidate changes (various delays, various padding amounts, keep-alive
values, and in the extended set QoS/retain combinations), throws away any that
would be invalid, and asks the detector about the rest. If any valid candidate
is called "legitimate", that is one successful evasion.

**What it reports** (per attack class, per model, per constraint set):

- **Attack success rate** — the share of attacks it managed to disguise. This
  is your RQ1 answer: how much detection survives a realistic attacker.
- **Detection recall, clean vs adversarial, and the drop** — the report's
  "detection rate degradation", the principal result.
- **Mean queries** and **mean fields changed** — how hard the attacker had to
  work, which speaks to realism.

The successful adversarial packets are saved to disk, because O3 needs them.

## 4. `phase3_defence.py` — the defence (O3)

**Primary defence: adversarial training.** The successful adversarial packets
from O2 are added back into the training data, labelled with their *true* attack
class (a disguised DoS packet is still a DoS packet). The model retrains and
learns not to be fooled by those disguises.

To test this honestly, the O2 samples are split in half: one half trains the
defence, the other half is **held out** to measure whether the *old* disguises
still work. Evaluating a defence on the very samples it trained on would be
cheating, so we do not.

**The decisive test: adaptive re-attack.** This is the step most published
defences skip, and your report (3.7) and panel both single it out. We run the
*whole O2 search again*, from scratch, against the **defended** model. The
attacker is not replaying old tricks; it is finding new ones against the new
detector. A defence only counts if the success rate stays low *here*.

So the table shows three things per model:
- clean macro F1 before and after the defence (what accuracy the defence costs),
- whether the **old** disguises still evade (static robustness),
- whether a **fresh** attack evades (adaptive robustness — the real test).

**Secondary defence (optional, `--harden`): feature hardening.** Retrain with
the shortcut fields (`mqtt.qos`, `mqtt.msgid`, `mqtt.hdrflags`) removed, so the
detector *cannot* lean on a lever the attacker controls. The report lists this
as the secondary mechanism; ensemble diversity is left as future work, exactly
as the report says.

## 5. `phase4_tradeoff.py` — the trade-off (O4)

No new training ideas here; it joins the numbers. For each model, baseline vs
adversarially trained, it records clean macro F1, robustness (100 − adaptive
attack success rate), inference latency per packet, and model size on disk, then
draws one scatter plot: robustness across the bottom, clean accuracy up the
side, an arrow from each baseline model to its defended version, marker size for
model size. That one picture is the deployability answer your panel's
"who would use this, and can it run on a gateway?" question wants.

## 6. What is honest about this, and what its limits are

- Every perturbation is checked against the MQTT rules in code, and the
  `mosquitto_testbed/` scripts confirm a real broker accepts a sample of them.
  That is the "protocol validity" column in your metrics table.
- **Limit 1:** validity is not the same as *effect*. The code proves a slowed or
  padded packet is legal MQTT; it does not prove a slowed DoS still overwhelms
  the broker. That needs a load test, which the report already lists as future
  work. Say this plainly.
- **Limit 2:** the attacker here can only *increase* padding, because the
  dataset does not let us shrink a real payload safely. If a DoS could also use
  *smaller* payloads, it might evade more easily; that is a question for the
  testbed, noted in the constraint table.
- **Limit 3:** this is still the MQTTset feature space. Cross-dataset work on
  MQTT-IoT-IDS2020 is the report's separate deliverable.

## 7. How to run it (on your Mac)

```bash
source ~/Downloads/P1/.venv/bin/activate
python3 src/run_phase2to4.py            # O2, O3, O4 end to end (~minutes)
```

For the protocol-validity confirmation, see `mosquitto_testbed/README.md`.
