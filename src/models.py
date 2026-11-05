"""
models.py — the three Phase 1 detectors, with the settings from the brief (F5).

Class imbalance is handled the same way for all three, by giving each training
row a weight inversely proportional to its class size ("balanced"):
  - Random Forest: class_weight='balanced' (built in)
  - XGBoost:       sample_weight = balanced weights (XGBoost has no class_weight)
  - MLP:           sample_weight = balanced weights, IF the installed scikit-learn
                   supports it (added in scikit-learn 1.7). Otherwise unweighted,
                   and the run log says so.
No oversampling (no SMOTE): synthetic packets may not be valid MQTT.
"""
import inspect

from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

import config

MODEL_NAMES = ["RandomForest", "XGBoost", "MLP"]

MLP_SUPPORTS_WEIGHTS = "sample_weight" in inspect.signature(MLPClassifier.fit).parameters


def make_model(name):
    if name == "RandomForest":
        return RandomForestClassifier(n_estimators=100, random_state=config.SEED,
                                      n_jobs=-1, class_weight="balanced")
    if name == "XGBoost":
        return XGBClassifier(tree_method="hist", random_state=config.SEED, n_jobs=-1,
                             importance_type="gain")
    if name == "MLP":
        # Scaling only for the MLP: trees do not need it.
        return Pipeline([
            ("scale", StandardScaler()),
            ("mlp", MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=300,
                                  random_state=config.SEED)),
        ])
    raise ValueError(name)


def fit_model(name, X, y_int):
    """Train one model. y_int = labels as integers 0..K-1."""
    model = make_model(name)
    if name == "RandomForest":
        model.fit(X, y_int)
    elif name == "XGBoost":
        model.fit(X, y_int, sample_weight=compute_sample_weight("balanced", y_int))
    elif name == "MLP":
        if MLP_SUPPORTS_WEIGHTS:
            model.fit(X, y_int, mlp__sample_weight=compute_sample_weight("balanced", y_int))
        else:
            model.fit(X, y_int)
    return model


def feature_importance(name, model, feature_names):
    """Importance per feature for tree models; None for the MLP."""
    if name in ("RandomForest", "XGBoost"):
        return dict(zip(feature_names, model.feature_importances_))
    return None
