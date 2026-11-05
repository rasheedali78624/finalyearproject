# Phase 1 · Task 1 — Duplication and Leakage Findings

**Source of every number below:** `src/dedup_analysis.py`, run by Rasheed on his
MacBook on 5 Nov 2026 (log `results/phase1/logs/task1_dedup_20261105_124023.txt`,
Python 3.14.2, pandas 3.0.6, runtime 10.3 s).
Numbers marked *derived* are simple arithmetic on logged values.

**To reproduce:** `source ~/Downloads/P1/.venv/bin/activate`, then
`python3 src/dedup_analysis.py` from the repository folder.

**Definition used:** a *feature vector* is all 33 columns except the label
`target`, compared as exact text. Two rows are duplicates if their feature
vectors are identical.

---

## 1. Constant columns — brief confirmed

12 constant columns, exactly the 12 listed in the brief → **21 usable features**.

## 2. The supplied train/test split is not an exact partition

| | Rows |
|---|---|
| Full file | 330,926 |
| train70 + test30 | 330,936 |
| Difference | **+10, all in class `dos`** |

All other classes match exactly. The test share is 30.00–30.02% for every
class, so the published split is stratified. The 10 extra `dos` rows are small
but should be mentioned as a property of the published benchmark.

## 3. Duplication per class (full file)

| Class | Total rows | Unique rows | Duplicate % |
|---|---|---|---|
| legitimate | 165,463 | 18,374 | 88.90 |
| slowite | 9,202 | 2,580 | 71.96 |
| bruteforce | 14,501 | 4,372 | 69.85 |
| malformed | 10,924 | 4,745 | 56.56 |
| flood | 613 | 332 | 45.84 |
| dos | 130,223 | 91,024 | 30.10 |

- Exact duplicate rows (features + label): **209,499 = 63.31%** — reproduces the brief.
- Duplicate feature vectors (label ignored): 210,948 = 63.74%.
- Unique feature vectors overall: 119,978.
- **No class is below 100 unique rows.** The smallest is `flood` with 332.

**Observations:**
- `legitimate` is the most repetitive class (88.90%). After de-duplication it
  shrinks from 50% of the data to about 15% (*derived*: 18,374 of 121,427
  unique class-rows), and `dos` becomes about 75%.
- The imbalance does **not** improve after de-duplication: the largest/smallest
  unique count is about 274 : 1 (*derived*: 91,024 / 332), against 270 : 1 before.

## 4. Label conflicts — the largest new finding

**1,129 distinct feature vectors appear with more than one label. They cover
110,711 rows = 33.45% of the dataset.**

| Class | Rows whose feature vector also appears under another label | % of class |
|---|---|---|
| bruteforce | 8,669 | 59.78 |
| flood | 304 | 49.59 |
| malformed | 4,649 | 42.56 |
| legitimate | 60,568 | 36.61 |
| dos | 36,521 | 28.04 |
| slowite | 0 | 0.00 |

The most common collision is `bruteforce + malformed` (697 vectors).

**What this means:** for these rows, the 33 features hold no information that
separates the classes. No model, however good, can classify all of them
correctly. A large part of any reported accuracy on this dataset depends on
which label each model assigns to the ambiguous vectors.

**Not yet verified (hypothesis only):** these rows may be packets with no
MQTT layer, such as TCP ACKs and handshakes. All their MQTT fields would then
read `0`, and they would be labelled by which capture file they came from.
Task 2 will check this.

## 5. Train/test leakage in the published split — full files, no sampling

| Class | Test rows | Also in train | % |
|---|---|---|---|
| legitimate | 49,639 | 46,358 | **93.39** |
| bruteforce | 4,351 | 3,412 | 78.42 |
| slowite | 2,761 | 2,059 | 74.57 |
| malformed | 3,278 | 2,356 | 71.87 |
| flood | 184 | 93 | 50.54 |
| dos | 39,077 | 12,154 | 31.10 |
| **Total** | **99,290** | **66,432** | **66.91** |

Of the 66,432 leaked test rows, 66,054 appear in train with the **same**
label. A model can therefore get those rows right by remembering them, not by
generalising.

**Correction:** the earlier figure of ~22.6% came from a sampled comparison of
unique tuples and was wrong. The measured figure is **66.91%** of test rows.

## 6. Text columns — 6, not 7

The brief counted 7 text columns, but one of them is the label `target`.
There are **6 text feature columns**:

| Column | Distinct values | Examples |
|---|---|---|
| tcp.flags | 8 | `0x00000018`, `0x00000010`, `0x00000011` |
| mqtt.conack.flags | 2 | `0`, `0x00000000` |
| mqtt.conflags | 4 | `0`, `0x00000002`, `0x000000c2` |
| mqtt.hdrflags | 14 | `0`, `0x00000030`, `0x00000040` |
| mqtt.protoname | 2 | `0`, `MQTT` |
| mqtt.msg | **50,054** | `0`, `30`, `31` |

Several columns mix a plain `0` with hex values such as `0x00000000`. The plain
`0` probably means "field not present in this packet", which is not the same
thing as a present field whose value is 0. Encoding must keep that distinction
(Task 2).

---

## Consequences for the rest of Phase 1

1. **The unique counts above are measured on raw text with all 33 columns.**
   Dropping `mqtt.msg` and converting hex to numbers will merge some rows that
   are currently distinct. Duplication, conflict and leakage therefore have to
   be **re-measured in the final model feature space**. The numbers in sections
   3–5 are the raw-data figures, not the figures the models will see.
2. **Variant B must split by feature vector, not by row.** All rows that share
   a feature vector must go to the same side of the split; otherwise the
   label-conflict rows leak across it. The planned tool is a grouped,
   stratified split (`StratifiedGroupKFold` in scikit-learn).
3. **Framing for the panel (Prof. Yamani's overfitting point):** two thirds of
   the published test set also appears in its training set, and one third of
   all rows cannot be separated on these features at all. Both facts bear
   directly on the 97–99% figures reported in the literature.

## Still uncertain

- The cause of the label conflicts (hypothesis in §4, not yet tested).
- How much duplication, conflict and leakage remain after encoding and after
  dropping `mqtt.msg` (Task 2).
- Why the split files contain 10 more `dos` rows than the full file.
