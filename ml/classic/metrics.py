"""Evaluation metrics shared by every scorer (sklearn, Keras, LoRA, LLM judge).

Scores are ORDINAL (1 < 2 < ... < 5), so plain accuracy is not enough: predicting 4 for a 5
is much better than predicting 1. We report:
- accuracy        exact match
- macro_f1        F1 per class averaged equally (doesn't let the big classes hide bad ones)
- mae             mean absolute error in score points
- within_1        share of predictions at most 1 point off
- qwk             quadratic weighted Cohen's kappa: agreement beyond chance, penalising big
                  disagreements quadratically; 1 = perfect, 0 = chance. Standard for essay scoring.
"""
from __future__ import annotations

import numpy as np


def evaluate(y_true, y_pred) -> dict:
    from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score, mean_absolute_error

    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.clip(np.rint(np.asarray(y_pred, dtype=float)), 1, 5).astype(int)
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 3),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro", labels=[1, 2, 3, 4, 5], zero_division=0)), 3),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 3),
        "within_1": round(float(np.mean(np.abs(y_true - y_pred) <= 1)), 3),
        "qwk": round(float(cohen_kappa_score(y_true, y_pred, weights="quadratic", labels=[1, 2, 3, 4, 5])), 3),
        "n": int(len(y_true)),
    }
