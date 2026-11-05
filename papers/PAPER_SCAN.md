# Paper review against the Phase 1 findings — 5 Nov 2026

**Method:** text extracted from each PDF with `pdftotext`. Key passages were
read for the papers marked **Read**; the rest were only keyword-checked for
which dataset they use. Quotes are from the PDF text. **Before citing any of
this, open the paper and check the passage yourself**, and check the reference
details.

**Question being answered:** do the published high MQTT results come from the
same data as Phase 1 (`mqttdataset_reduced.csv`, 6 classes, 20 features), so
that the 93.27% ceiling and the leakage findings apply to them?

---

## Short answer

1. **Almost none of the high (99%+) MQTT results in this folder use MQTTset.**
   They use MQTT-IoT-IDS2020, IoT-23, TON_IoT, CICIoT2023, Bot-IoT, NSL-KDD or
   the authors' own data. The 93.27% ceiling **does not apply to them**, and
   must not be quoted against them.
2. **Only one paper here reports its own results on MQTTset: paper 15.** It is
   not comparable with Phase 1: it drops two of the six classes, uses SMOTE,
   reports weighted F1 only, does not mention duplicates, and gives three
   different headline figures.
3. **One paper, 23, does remove duplicate records**, but on a different, merged
   MQTT dataset with 3 classes. It is the closest earlier work to Phase 1's
   de-duplication and must be cited. No paper here measures leakage in a
   published split, or the label ambiguity of bare TCP packets.

---

## Papers that use MQTT data

| # | Paper | Dataset | Status |
|---|---|---|---|
| **15** | Shibi, "Intrusion Detection for MQTT IoT Traffic using Evolutionary Feature Selection, Ensemble Learning, and Explainable AI", ICoICI 2025, IEEE. DOI 10.1109/ICoICI65217.2025.11253413 | **MQTTSet** | **Read** (see below) |
| **23** | Díaz-Longueira et al., "Shallow Learning Techniques for Early Detection and Classification of Cyberattacks over MQTT IoT Networks", *Sensors* 2026, 26, 468. DOI 10.3390/s26020468 | Three MQTT datasets merged (66 variables, 3 classes); not MQTTset | **Read** (see below) |
| 17 | Muñoz Castañeda et al., "Characterization of threats in IoT from an MQTT protocol-oriented dataset", *Complex & Intelligent Systems* 2023, 9:5281–5296. DOI 10.1007/s40747-023-01000-y | Authors generate their own MQTT traffic; MQTTset and MQTT-IoT-IDS2020 appear in the related-work table | Partly read: uses `mqtt.msg` as a feature; reports e.g. 0.99377 accuracy on its own data |
| 18 | Chesney, "AI Empowered Intrusion Detection for MQTT Networks", icABCD 2022, IEEE. DOI 10.1109/icABCD54961.2022.9856124 | **MQTT-IoT-IDS2020** ("The target dataset was the MQTT-IoT-IDS2020 dataset") | Dataset checked |
| 14 | "Enhanced Intrusion Detection in IoT Smart Homes", DOI 10.3991/ijoe.v21i05.53485 | MQTT-IoT-IDS2020 | Keyword check only |
| 21 | "Deep Learning for Improved MQTT-Based Security Detection in IoT Systems", DOI 10.1109/IC363308.2025.10956964 | MQTT-IoT-IDS2020 | Keyword check only |
| 6 | "AI-Driven Real-Time Intrusion Detection… Industrial IoT…", DOI 10.1109/ICOEI68323.2026.11542157 | IoT-23 and MQTT-IoT-IDS2020 | Keyword check only |
| 20 | "Evaluating ML Techniques on Big Data Frameworks for MQTT IoT Security", DOI 10.1109/I3CTCON68242.2026.11508116 | MQTT-IoT-IDS2020, IoT-23, CICIDS2017 mentioned | Keyword check only |
| 19 | "DDoS Attack Detection on MQTT Protocol Using Semi-supervised DBSCAN and SVM", DOI 10.1109/ICoICT58202.2023.10262594 | No public dataset named, probably the authors' own | Keyword check only |
| 5 | Isha, "Intrusion Detection and Prevention in MQTT-Based IoT Networks: A Comprehensive Review", IIPEM 2025, IEEE. DOI 10.1109/IIPEM65914.2025.11548093 | Review | Table read (see below) |

**Not MQTT-specific** (useful for O2/O3, not for the 97–99% comparison):
- 8: TON_IoT / UNSW-NB15 / Bot-IoT
- 11: CICIoT2023
- 13: NSL-KDD / Bot-IoT
- 1, 2, 12: MQTT security, but not ML benchmarks
- 3 (PANDA), 4, 7, 9, 10 (TAD), 16, 22, 24, 25, 26: adversarial ML / NIDS

---

## Paper 15 (the one MQTTset results paper): details

What its text says:
- "The experiment utilizes the MQTTSet dataset". **The file (reduced, full or
  augmented) is not named** in the text I read.
- **"Two noise-heavy classes—Malformed and SlowITe are excluded from the
  training process."** So it is a 4-class problem. In Phase 1, `malformed` is
  the hardest class, with the lowest recall for every model.
- Categorical fields: ordinal encoding. Feature selection "from 34 to 25", but
  the conclusion says "34 to 24". It starts from all 34 columns, so it likely
  includes `mqtt.msg`, but **the selected features are not listed in the text I
  read**.
- **SMOTE** is used for class balancing. The text says it generates "a balanced
  training dataset", but whether that happens before or after the
  cross-validation split is not clear from the text.
- Stratified 5-fold cross-validation. **No mention of duplicates or of
  train/test overlap.**
- Results are given three ways:
  - "cross-validated accuracy of 96.5% and a weighted F1-score of 96.5%"
  - ablation table: "accuracy of 94.64% and a weighted F1-score of 0.95"
  - conclusion: "95.0% accuracy and a weighted F1-score of 0.95"
- Weighted F1 only; no macro F1.
- Its comparison table lists two more MQTTset papers **that are not in this
  folder**: Zeghida et al. (2023), about 95%, and Prajisha & Vasudevan (2022),
  about 96%, LightGBM. **Find and read these before citing them**; their numbers
  here are second-hand.

**How to use it in your report:** as an example of the usual protocol:
- a random stratified split with no duplicate handling;
- SMOTE;
- weighted F1 only;
- the hardest classes dropped.

Each of those differs from your Phase 1 design. Do **not** say its 96.5% is
"impossible" because of the 93.27% ceiling. The ceiling is for 6 classes and
our 20 features; paper 15 uses 4 classes and different features, so the
ceilings are not the same.

## Paper 23 (the de-duplication paper): details

What its text says:
- Three MQTT datasets were merged: "more than 260,000 registers, with 66
  predictor variables", 3 classes (normal + two attacks). **Not MQTTset.**
- Removed "network identifiers, message contents, topic names, IP and MAC
  addresses", for the same reason you dropped `mqtt.msg`: they could bias the
  model.
- Missing values "imputed with an out-of-range value (−1)". This is the same
  idea as your "absent = −1" encoding.
- **"duplicate records were detected and removed, reducing the set to
  approximately 175,000 unique records"**, then 10-fold stratified
  cross-validation on 75%, with "oversampling … used only on the models'
  training set".

**How it relates to your work:** it is prior work that de-duplicates
correctly and applies oversampling only to training data. Cite it as support
for your approach. Your contribution goes further, because you:
1. measure leakage in the **published MQTTset split** (69.59%);
2. find that 99.89% of label conflicts are bare TCP packets, and measure the
   resulting accuracy ceiling;
3. split Variant A's test set into memorised, ambiguous and unseen rows;
4. find the `slowite` `0.0` payload artefact.

It is not clear from the text whether paper 23 removed rows with identical
features but different labels. Check that when you read it.

## Paper 5 (review): a warning

Its comparison table says Vaccari et al. (2020), the MQTTset paper, reached
"Accuracy ≈ 97%" on "DoS, spoofing, malformed packets". **MQTTset has no
spoofing class.** Its classes are legitimate, dos, flood, bruteforce,
malformed and slowite. So this review's table is not reliable for exact
figures. **Never cite a number from a review table. Go to the original paper.**
The same table lists "Khan et al. (2022) … MQTTset / custom … Accuracy 99%",
which also needs checking at the source.

---

## What to say to Dr. Bryan

"Most of the 99% MQTT results in my reading list use MQTT-IoT-IDS2020 or
other datasets, so my MQTTset ceiling doesn't apply to them. The one MQTTset
results paper I have drops the two hardest classes, uses SMOTE, reports
weighted F1 only and never mentions duplicates. One 2026 paper does
de-duplicate, on a different MQTT dataset, which supports my approach. But
none measure leakage in a published split or the bare-TCP label ambiguity."

## Reading list, in order

1. **Paper 15**: read the method in full. Find the MQTTset file used, the
   selected features (is `mqtt.msg` in them?), and when SMOTE is applied.
2. **Paper 23**: Section 4 in full: the three source datasets, and how the
   duplicates were defined.
3. **The original MQTTset paper** (Vaccari et al., 2020, *Sensors*). It is not in
   this folder; you need it to cite the dataset and its attack definitions.
4. **Zeghida et al. (2023)** and **Prajisha & Vasudevan (2022)**: the other
   MQTTset results papers, found via paper 15's table.
5. For O2: papers 3 (PANDA), 16 (Automatic Evasion of ML-based NIDS), 24 and
   25 (adversarial attacks against NIDS). These are the methods Phase 2 will
   build on.
