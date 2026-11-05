"""
evaluate.py — metrics, latency, model size and plots.

Metric definitions (all from scikit-learn):
  per-class precision / recall / F1
  macro F1     = plain average of the per-class F1 scores   <- HEADLINE
  weighted F1  = average weighted by class size              (secondary)
  accuracy                                                   (reported, never headline)
  FPR          = share of 'legitimate' rows predicted as any attack class
"""
import os
import time

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_recall_fscore_support)

import config


def scores(y_true, y_pred, classes):
    """All metrics for one set of predictions (labels as integers)."""
    labels = list(range(len(classes)))
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels,
                                                 zero_division=0)
    normal = classes.index(config.NORMAL_CLASS)
    is_normal = y_true == normal
    fpr = float(np.mean(y_pred[is_normal] != normal)) if is_normal.any() else float("nan")
    out = {
        "macro_f1": f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", labels=labels, zero_division=0),
        "accuracy": accuracy_score(y_true, y_pred),
        "fpr": fpr,
    }
    for i, c in enumerate(classes):
        out[f"precision_{c}"] = p[i]
        out[f"recall_{c}"] = r[i]
        out[f"f1_{c}"] = f[i]
        out[f"support_{c}"] = int(s[i])
    return out


def latency_ms(model, X, repeats=3, single_rows=200):
    """
    Two latency figures, in milliseconds per sample:
      batch  : predict the whole test set at once, divide by rows (median of repeats)
      single : predict one row at a time (like a live IDS), median over `single_rows`
    Timing varies slightly between runs and machines; it is NOT bit-for-bit reproducible.
    """
    Xn = np.asarray(X)
    batch = []
    for _ in range(repeats):
        t = time.perf_counter(); model.predict(Xn); batch.append(time.perf_counter() - t)
    single = []
    for i in range(min(single_rows, len(Xn))):
        row = Xn[i:i + 1]
        t = time.perf_counter(); model.predict(row); single.append(time.perf_counter() - t)
    return 1000 * np.median(batch) / len(Xn), 1000 * float(np.median(single))


def save_model(model, path):
    joblib.dump(model, path)
    return os.path.getsize(path) / 1024.0


def plot_confusion(y_true, y_pred, classes, title, path):
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(classes))))
    with np.errstate(invalid="ignore", divide="ignore"):
        cm_norm = cm / cm.sum(axis=1, keepdims=True)
    fig, ax = plt.subplots(figsize=(7.2, 6))
    im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(classes)), classes, rotation=35, ha="right")
    ax.set_yticks(range(len(classes)), classes)
    ax.set_xlabel("Predicted class"); ax.set_ylabel("True class")
    for i in range(len(classes)):
        for j in range(len(classes)):
            v = cm_norm[i, j]
            ax.text(j, i, f"{cm[i, j]:,}\n{v:.1%}" if cm[i, j] else "0",
                    ha="center", va="center", fontsize=7.5,
                    color="white" if v > 0.55 else "black")
    ax.set_title(title, fontsize=11)
    fig.colorbar(im, ax=ax, fraction=0.046, label="share of true class (row)")
    fig.tight_layout(); fig.savefig(path, dpi=config.FIG_DPI); plt.close(fig)


def plot_macro_f1(table, path):
    """table: DataFrame with columns model, variant, macro_f1 (test)."""
    models = list(dict.fromkeys(table["model"]))
    x = np.arange(len(models)); w = 0.36
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for k, (v, col) in enumerate([("A", "#9bb7c9"), ("B", "#1f5f7a")]):
        vals = [float(table[(table.model == m) & (table.variant == v)]["macro_f1"].iloc[0])
                for m in models]
        bars = ax.bar(x + (k - 0.5) * w, vals, w, label=f"Variant {v}", color=col)
        for b, val in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, val + 0.01, f"{val:.3f}",
                    ha="center", fontsize=8)
    ax.set_xticks(x, models); ax.set_ylim(0, 1.08); ax.set_ylabel("Macro F1 (held-out test)")
    ax.set_title("Macro F1: as-published split (A) vs de-duplicated split (B)", fontsize=11)
    ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(path, dpi=config.FIG_DPI); plt.close(fig)


def plot_per_class_recall(row, classes, title, path):
    vals = [row[f"recall_{c}"] for c in classes]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.barh(classes, vals, color="#1f5f7a")
    for b, v in zip(bars, vals):
        ax.text(min(v + 0.01, 0.93), b.get_y() + b.get_height() / 2, f"{v:.3f}",
                va="center", fontsize=8)
    ax.set_xlim(0, 1); ax.invert_yaxis(); ax.set_xlabel("Recall (held-out test)")
    ax.set_title(title, fontsize=11); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(path, dpi=config.FIG_DPI); plt.close(fig)


def plot_importance(imp, title, path, top=15):
    items = sorted(imp.items(), key=lambda kv: kv[1], reverse=True)[:top]
    names = [k for k, _ in items][::-1]; vals = [v for _, v in items][::-1]

    def colour(n):
        if n in config.MUTABLE_FIELDS: return "#c0392b"
        if n in config.IMMUTABLE_FIELDS: return "#2e7d4f"
        return "#7f8c8d"
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.barh(names, vals, color=[colour(n) for n in names])
    ax.set_yticks(range(len(names)), [f"{n}  [{'TCP' if n.startswith('tcp.') else 'MQTT'}]"
                                      for n in names], fontsize=8.5)
    ax.set_xlabel("Importance")
    ax.set_title(title, fontsize=11)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#c0392b", label="attacker-mutable (report, O2)"),
                       Patch(color="#2e7d4f", label="immutable (report, O2)"),
                       Patch(color="#7f8c8d", label="not yet classified")],
              frameon=False, fontsize=8, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(path, dpi=config.FIG_DPI); plt.close(fig)
