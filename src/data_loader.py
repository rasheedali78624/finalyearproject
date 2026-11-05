"""
data_loader.py — load MQTTset, turn text into numbers, build Variants A and B.

ENCODING RULES (Step 2). Every rule is checked: an unexpected value stops the
program with an error instead of being silently guessed.

  1. Drop the 12 constant columns (config.BRIEF_CONSTANT_COLS) — they never vary.
  2. Drop mqtt.msg (config.DROPPED_COLS) — payload text, 50,054 distinct values.
  3. Hex columns (values like '0x00000018'): convert to an integer.
     A plain '0' in these columns means "field not in this packet" — it is kept
     apart from a real zero ('0x00000000') by encoding it as -1 (ABSENT_VALUE).
  4. mqtt.protoname: '0' (absent) -> 0, 'MQTT' -> 1.
  5. Every other column is already a number and is read as a float.

VARIANTS
  A  "as published": train70_reduced.csv / test30_reduced.csv, unmodified.
  B  "de-duplicated": from the full file, keep one row per (feature vector, label),
     then split 70/30 so that ALL rows sharing a feature vector land on the same
     side (grouped + stratified). The test set then contains no packet shape the
     model has seen in training.
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

import config
from utils import row_key

HEX_PREFIX = "0x"
CATEGORICAL_MAPS = {"mqtt.protoname": {"0": 0, "MQTT": 1}}


def load_raw(path):
    """Read a CSV keeping every value as the exact text in the file."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Set MQTT_DATA_DIR or check config.DATA_DIR."
        )
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def feature_columns(raw):
    """The columns the models use, in file order."""
    removed = set(config.BRIEF_CONSTANT_COLS) | set(config.DROPPED_COLS) | {config.LABEL_COL}
    return [c for c in raw.columns if c not in removed]


def _encode_hex(s, name):
    out = np.empty(len(s), dtype=float)
    is_hex = s.str.startswith(HEX_PREFIX)
    is_absent = s == "0"
    bad = ~(is_hex | is_absent)
    if bad.any():
        raise ValueError(f"{name}: unexpected values {s[bad].unique()[:5]}")
    out[is_hex.to_numpy()] = [int(v, 16) for v in s[is_hex]]
    out[is_absent.to_numpy()] = config.ABSENT_VALUE
    return out


def encode_column(s, name):
    """Return (numeric array, rule description) for one raw text column."""
    if name in CATEGORICAL_MAPS:
        mapping = CATEGORICAL_MAPS[name]
        unknown = set(s.unique()) - set(mapping)
        if unknown:
            raise ValueError(f"{name}: values not in mapping: {unknown}")
        return s.map(mapping).to_numpy(dtype=float), f"category map {mapping}"
    if s.str.startswith(HEX_PREFIX).any():
        return _encode_hex(s, name), "hex -> integer; plain '0' (absent) -> -1"
    num = pd.to_numeric(s, errors="coerce")
    if num.isna().any():
        raise ValueError(f"{name}: non-numeric values {s[num.isna()].unique()[:5]}")
    return num.to_numpy(dtype=float), "numeric (float)"


def encode(raw):
    """Raw text frame -> (X: numeric DataFrame, y: label Series, rules: dict)."""
    cols = feature_columns(raw)
    X, rules = {}, {}
    for c in cols:
        X[c], rules[c] = encode_column(raw[c], c)
    X = pd.DataFrame(X, index=raw.index)
    y = raw[config.LABEL_COL].reset_index(drop=True)
    return X.reset_index(drop=True), y, rules


def variant_a():
    """Supplied split, unmodified (only encoded)."""
    Xtr, ytr, _ = encode(load_raw(config.TRAIN_CSV))
    Xte, yte, _ = encode(load_raw(config.TEST_CSV))
    return {"name": "A", "X_train": Xtr, "y_train": ytr, "X_test": Xte, "y_test": yte,
            "groups_train": None}


def variant_b(X_full=None, y_full=None):
    """De-duplicated, grouped + stratified 70/30 split of the full file."""
    if X_full is None:
        X_full, y_full, _ = encode(load_raw(config.FULL_CSV))
    df = X_full.copy()
    df["_y"] = y_full.to_numpy()
    df = df.drop_duplicates().reset_index(drop=True)          # one row per (vector, label)
    feats = [c for c in df.columns if c != "_y"]
    groups = pd.factorize(row_key(df, feats))[0]              # same vector -> same group id

    sgkf = StratifiedGroupKFold(n_splits=config.VARIANT_B_TOTAL_FOLDS, shuffle=True,
                                random_state=config.SEED)
    fold_of = np.empty(len(df), dtype=int)
    for k, (_, idx) in enumerate(sgkf.split(df[feats], df["_y"], groups)):
        fold_of[idx] = k
    test_mask = fold_of < config.VARIANT_B_TEST_FOLDS

    tr, te = df[~test_mask].reset_index(drop=True), df[test_mask].reset_index(drop=True)
    # Safety check: no feature vector may appear on both sides.
    crossing = set(groups[~test_mask]) & set(groups[test_mask])
    if crossing:
        raise RuntimeError(f"Variant B split leaks {len(crossing)} feature vectors")
    return {"name": "B",
            "X_train": tr[feats], "y_train": tr["_y"],
            "X_test": te[feats], "y_test": te["_y"],
            "groups_train": groups[~test_mask]}
