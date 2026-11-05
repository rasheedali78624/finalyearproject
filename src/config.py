"""
config.py — every path, seed and constant for Phase 1 lives here.

Why a separate file: if a path or seed is written in five scripts, sooner or
later one of them is different. Here it is written once and imported everywhere.
"""
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# Folder that contains this repository (one level above src/).
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Where the MQTTset CSV files are. Default = the location on Rasheed's Mac.
# To use another location without editing code:
#   export MQTT_DATA_DIR=/some/other/folder
DATA_DIR = Path(
    os.environ.get(
        "MQTT_DATA_DIR",
        Path.home() / "Downloads" / "P1" / "Datasets" / "MQTTset" / "Data" / "FINAL_CSV",
    )
)

FULL_CSV = DATA_DIR / "mqttdataset_reduced.csv"   # primary file
TRAIN_CSV = DATA_DIR / "train70_reduced.csv"      # supplied train split (Variant A)
TEST_CSV = DATA_DIR / "test30_reduced.csv"        # supplied test split  (Variant A)

# All outputs go here. Raw data files are only ever READ, never written.
RESULTS_DIR = PROJECT_ROOT / "results" / "phase1"
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR = RESULTS_DIR / "figures"
MODELS_DIR = RESULTS_DIR / "models"
LOGS_DIR = RESULTS_DIR / "logs"

# ---------------------------------------------------------------------------
# Experiment constants
# ---------------------------------------------------------------------------
SEED = 42                 # used for every random operation
LABEL_COL = "target"      # name of the label column in MQTTset

# A class with fewer unique samples than this is flagged as too small to
# support a reliable performance estimate.
MIN_UNIQUE_WARN = 100

# The 12 zero-variance columns listed in the build brief (from step1_explore.py
# on 16 Oct). The analysis RE-COMPUTES constant columns from the data and
# compares against this list — it does not trust the list blindly.
BRIEF_CONSTANT_COLS = [
    "mqtt.conack.flags.reserved",
    "mqtt.conack.flags.sp",
    "mqtt.conflag.qos",
    "mqtt.conflag.reserved",
    "mqtt.conflag.retain",
    "mqtt.conflag.willflag",
    "mqtt.sub.qos",
    "mqtt.suback.qos",
    "mqtt.willmsg",
    "mqtt.willmsg_len",
    "mqtt.willtopic",
    "mqtt.willtopic_len",
]


def ensure_output_dirs():
    """Create the results folders if they do not exist yet."""
    for d in (TABLES_DIR, FIGURES_DIR, MODELS_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Step 2: encoding decisions (see data_loader.py for the rules)
# ---------------------------------------------------------------------------
# Dropped on purpose, in addition to the 12 constant columns:
#   mqtt.msg = the message payload. 50,054 distinct values (Task 1), so a model
#   could memorise payload content; and it is fully attacker-controlled. Dropping
#   it REMOVES it from the O2 constraint set — this must be stated in the report.
DROPPED_COLS = ["mqtt.msg"]

# Value used for "field not present in this packet" in hex columns.
# Hex columns write a plain '0' when the field is absent, and '0x00000000' when
# it is present with value zero. We keep those apart: absent -> -1.
ABSENT_VALUE = -1

# ---------------------------------------------------------------------------
# Models and evaluation
# ---------------------------------------------------------------------------
CV_SPLITS = 5
CV_REPEATS = 3
VARIANT_B_TEST_FOLDS = 3      # Variant B test = 3 of 10 grouped folds = ~30%
VARIANT_B_TOTAL_FOLDS = 10
NORMAL_CLASS = "legitimate"   # used for the false positive rate
FIG_DPI = 160

# Phase 2 constraint groups as written in the submitted report (brief, H4).
# Used only to annotate feature-importance plots. Not yet validated.
MUTABLE_FIELDS = ["tcp.time_delta", "tcp.len", "mqtt.kalive", "mqtt.len"]
IMMUTABLE_FIELDS = ["mqtt.msgtype", "mqtt.protoname", "mqtt.ver", "mqtt.conflags"]
