"""A tiny PyTorch MLP: 51 landmark features -> P(attentive).

Concept — MLP (multi-layer perceptron): layers of `y = activation(W x + b)`. With ReLU
activations and two hidden layers it can learn non-linear rules like "head slightly turned
is fine *unless* the eyes also look away". ~2.3k parameters: trains in seconds on a CPU and
runs in microseconds, so it can score every frame of every user live.

Standardization: inputs are shifted/scaled to mean 0, std 1 using statistics from the
*training* set; the same numbers must be applied at inference, so they're saved in the
checkpoint next to the weights.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np

from app.config import get_settings
from app.vision.features import FEATURE_DIM, FEATURE_VERSION, heuristic_attentive_prob, to_features

log = logging.getLogger(__name__)
MODEL_FILE = "attention_mlp.pt"


def build_mlp(input_dim: int = FEATURE_DIM, hidden: tuple[int, int] = (32, 16), dropout: float = 0.2):
    import torch.nn as nn

    return nn.Sequential(
        nn.Linear(input_dim, hidden[0]),
        nn.ReLU(),
        nn.Dropout(dropout),  # randomly zero 20% of activations while training -> less overfitting
        nn.Linear(hidden[0], hidden[1]),
        nn.ReLU(),
        nn.Linear(hidden[1], 1),  # one logit; sigmoid(logit) = probability of "attentive"
    )


class AttentionPredictor:
    """Loads the trained model if present, otherwise uses the heuristic."""

    def __init__(self, path: Path | None = None):
        self.path = path or Path(get_settings().models_dir) / MODEL_FILE
        self.model = None
        self.mean = self.std = None
        self.metrics: dict = {}
        if self.path.exists():
            self._load()

    @property
    def kind(self) -> str:
        return "mlp" if self.model is not None else "heuristic"

    def _load(self) -> None:
        import torch

        ckpt = torch.load(self.path, map_location="cpu", weights_only=False)
        if ckpt.get("feature_version") != FEATURE_VERSION:
            log.warning("attention model feature_version mismatch; using heuristic")
            return
        model = build_mlp(ckpt["input_dim"], tuple(ckpt["hidden"]))
        model.load_state_dict(ckpt["state_dict"])
        model.eval()  # disables dropout
        self.model = model
        self.mean = np.asarray(ckpt["mean"], dtype=np.float32)
        self.std = np.asarray(ckpt["std"], dtype=np.float32)
        self.metrics = ckpt.get("metrics", {})
        log.info("loaded attention model %s (%s)", self.path, self.metrics)

    def predict_proba(self, frames: list[list[float]]) -> np.ndarray:
        feats = to_features(frames)
        if self.model is None:
            return heuristic_attentive_prob(feats)
        import torch

        x = torch.from_numpy((feats - self.mean) / self.std)
        with torch.no_grad():  # inference only: no gradient bookkeeping
            return torch.sigmoid(self.model(x)).squeeze(1).numpy()


_predictor: AttentionPredictor | None = None
_lock = threading.Lock()


def get_predictor() -> AttentionPredictor:
    global _predictor
    with _lock:
        if _predictor is None:
            _predictor = AttentionPredictor()
    return _predictor


def reset_predictor() -> None:
    global _predictor
    _predictor = None
