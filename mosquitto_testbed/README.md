# Mosquitto testbed — protocol-validity confirmation for O2

**Why this exists.** The O2 attack (`src/phase2_attacks.py`) perturbs *feature
vectors* and checks each against the MQTT 3.1.1 rules in `src/constraints.py`.
That proves a perturbation is valid *on paper*. This testbed proves it on a
*real broker*: it rebuilds a perturbed packet, sends it to a live Eclipse
Mosquitto broker, and confirms the broker accepts it and acts on it. The share
of perturbations the broker accepts is the **protocol-validity rate** in the
report's Table 3.6.

This runs on your Mac, not in the cloud. It needs a broker, which the cloud
session cannot host.

## 1. Install the broker (once)

```bash
brew install mosquitto
```

## 2. Start a broker that allows anonymous connections (one terminal)

```bash
mosquitto -c mosquitto_testbed/mosquitto.conf -v
```

Leave it running. `-v` prints every packet it receives, so you can see the
perturbed packets arrive.

## 3. Run the validity check (a second terminal)

```bash
source ~/Downloads/P1/.venv/bin/activate
pip install paho-mqtt            # one-time, the MQTT client library
python3 mosquitto_testbed/replay_check.py
```

It reconstructs a sample of the O2 perturbations as real MQTT packets, sends
each to the broker, and reports how many the broker accepted. It writes
`results/phase2/tables/protocol_validity_rate.csv`.

## What it does and does not prove

- It **does** prove the perturbed packets are legal MQTT that a broker accepts.
- It does **not** by itself prove the attack still has its *effect* (e.g. that a
  slowed DoS still exhausts the broker). Measuring effect needs a load test,
  which is noted as future work in the report.

## The four testbed questions (from the constraint table)

Answer these here and record them for the report:
1. Does a DoS still overload the broker at QoS 0? (needs a load/timing test)
2. What `tcp.len` does one MQTT packet of a given `mqtt.len` actually produce?
3. Does the broker, as configured, allow anonymous login?
4. What timing range still lets each flooding attack overload the broker?
