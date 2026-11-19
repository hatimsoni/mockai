"""Serve the scikit-learn answer-quality baseline (trained in ml/classic/train_sklearn.py).

It's a second, cheap, deterministic opinion next to the LLM evaluator:
- shown in the report as "baseline model" for comparison,
- used by the Evaluator's fallback when the LLM is unavailable.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

from app.config import get_settings

log = logging.getLogger(__name__)
MODEL_FILE = "quality_baseline.joblib"

_model = None
_loaded = False
_lock = threading.Lock()


def model_input(question: str, answer: str) -> str:
    """The exact text format the model was trained on (imported by the training script)."""
    return f"{question or ''} [SEP] {answer or ''}"


def _get_model():
    global _model, _loaded
    with _lock:
        if not _loaded:
            path = Path(get_settings().models_dir) / MODEL_FILE
            if path.exists():
                import joblib

                try:
                    _model = joblib.load(path)
                except Exception as err:  # noqa: BLE001 - e.g. scikit-learn version mismatch
                    log.warning("could not load %s: %s", path, err)
            _loaded = True
    return _model


def reset() -> None:
    global _model, _loaded
    _model, _loaded = None, False


def predict(question: str, answer: str) -> dict | None:
    """{score: expected value 1-5, label: most likely class, probabilities} or None if no model."""
    model = _get_model()
    if model is None or not (answer or "").strip():
        return None
    probs = model.predict_proba([model_input(question, answer)])[0]
    classes = [int(c) for c in model.classes_]
    # expected value of the class distribution -> a smooth score (e.g. 3.6) instead of a hard 4
    expected = sum(p * c for p, c in zip(probs, classes, strict=True))
    return {
        "score": round(float(expected), 2),
        "label": classes[int(probs.argmax())],
        "probabilities": {str(c): round(float(p), 3) for c, p in zip(classes, probs, strict=True)},
    }
