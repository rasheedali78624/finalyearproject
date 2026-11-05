# Automated scan of the 26 papers — 5 Nov 2026 (first pass only)

**How it was made:** `pdftotext` on each PDF, then counting keyword matches.
This is a **keyword count, not a reading**. Nothing here is a finding until
someone has read the paper. "max %" is the largest "9x.x%" figure anywhere in
the text: it may be from the paper's own results, a related-work table or a
quoted claim.

| # | Paper (file name) | MQTTset mentions | MQTT-IoT-IDS2020 mentions | "duplicat" | "mqtt.msg" | Max % in text |
|---|---|---|---|---|---|---|
| 1 | Securing MQTT Ecosystem | 1 | 2 | 1 | 0 | – |
| 5 | Intrusion Detection and Prevention in MQTT-Based IoT (review) | 7 | 3 | 0 | 0 | – |
| 6 | AI-Driven Real-Time ID, Industrial IoT | 0 | 6 | 0 | 0 | 98.93 |
| 8 | IoT ID framework based on feature… | 0 | 0 | 1 | 0 | 99.99 |
| 10 | TAD Transfer Learning (Islam) | 0 | 0 | 9 | 0 | 99.99 |
| 14 | Enhanced ID in IoT Smart Homes | 0 | 5 | 0 | 0 | 99.99 |
| **15** | **ID for MQTT IoT Traffic, Evolutionary Feature Selection, Ensemble, XAI** | **12** | 0 | 0 | 3 | 96.5 |
| 17 | Characterization of threats… MQTT dataset (MQTTset authors' paper?) | 2 | 6 | 0 | 19 | – |
| 18 | AI Empowered ID for MQTT Networks | 3 | 9 | 0 | 0 | – |
| 19 | DDoS Detection on MQTT, DBSCAN + SVM | 0 | 0 | 0 | 0 | 99.9 |
| 20 | ML on Big Data Frameworks for MQTT IoT Security | 0 | 1 | 1 | 0 | – |
| 21 | DL for MQTT-Based Security Detection | 0 | 2 | 0 | 0 | 99.96 |
| 23 | Shallow Learning Techniques for Early Detection | 1 | 2 | 3 | 0 | 99.9 |

Papers 2, 3, 4, 7, 9, 11, 12, 13, 16, 22, 24, 25, 26 have no MQTTset or
MQTT-IoT-IDS2020 mentions. Most are adversarial-ML or general NIDS papers,
useful for O2/O3, not for the 97–99% comparison.

## What this suggests (to be checked by reading)

1. **Only paper 15 is clearly an MQTTset results paper.** Most of the high MQTT
   figures (99.9%+) come from papers that use MQTT-IoT-IDS2020 or other data.
   The 93.27% ceiling applies only to MQTTset `mqttdataset_reduced.csv` with our
   20 features, so it does **not** apply to those papers.
2. **Paper 15, from lines found in its text:**
   - "reduced the feature space from 34 to 25", so it likely started from all
     columns, probably including `mqtt.msg`
   - stratified 5-fold cross-validation
   - cross-validated accuracy 96.5% and weighted F1 96.5%
   - 94.64% accuracy and weighted F1 0.95
   - Its comparison table (around text lines 811–839) lists other MQTTset papers.

   **To check when reading:** which MQTTset file it used, whether duplicates
   were removed before cross-validation, whether `mqtt.msg` was kept, and
   whether 94.64% is on a held-out test set.
3. **No paper's text mentions train/test leakage of duplicates for MQTT data.**
   Papers 10, 23 and 26 contain the word "duplicat"; check what they say.

## Next step

Read paper 15 in full, then papers 17, 5 and 18. Fill in for each: dataset
file, features, split method, duplicates handled (yes/no), headline metric.
