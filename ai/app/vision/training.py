"""Training loop for the attention MLP (used by ml/vision/train_attention.py and tests).

Key ideas:
- **Group split**: frames from the same recording are nearly identical. If some land in train
  and others in test, test accuracy is fake-high ("leakage"). We split by recording id.
- **BCEWithLogitsLoss**: binary cross-entropy on the raw logit (numerically stable sigmoid).
- **pos_weight** compensates class imbalance (e.g. more attentive than away frames).
- **Early stopping**: keep the weights from the epoch with the best validation loss.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np

from app.vision.features import FEATURE_DIM, FEATURE_VERSION, to_features
from app.vision.model import build_mlp


@dataclass
class TrainResult:
    checkpoint: dict
    metrics: dict


def group_split(groups: np.ndarray, test_frac: float = 0.2, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """Boolean masks (train, test) with whole groups (recordings) on one side."""
    rng = np.random.default_rng(seed)
    unique = np.array(sorted(set(groups)))
    rng.shuffle(unique)
    n_test = max(1, round(len(unique) * test_frac)) if len(unique) > 1 else 0
    test_groups = set(unique[:n_test])
    test = np.array([g in test_groups for g in groups])
    return ~test, test


def _metrics(y_true: np.ndarray, prob: np.ndarray) -> dict:
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

    pred = (prob >= 0.5).astype(int)
    out = {
        "accuracy": round(float(accuracy_score(y_true, pred)), 4),
        "f1": round(float(f1_score(y_true, pred, zero_division=0)), 4),
        "n": int(len(y_true)),
    }
    if len(set(y_true)) == 2:
        out["roc_auc"] = round(float(roc_auc_score(y_true, prob)), 4)
    return out


def train_attention(
    frames: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    epochs: int = 200,
    lr: float = 1e-3,
    patience: int = 20,
    seed: int = 42,
) -> TrainResult:
    import torch

    torch.manual_seed(seed)
    feats = to_features(frames)
    y = labels.astype(np.float32)
    train_m, test_m = group_split(groups, seed=seed)
    if test_m.sum() == 0:  # single recording: fall back to a random 80/20 split
        rng = np.random.default_rng(seed)
        test_m = rng.random(len(y)) < 0.2
        train_m = ~test_m

    mean = feats[train_m].mean(0)
    std = feats[train_m].std(0) + 1e-6
    xtr = torch.from_numpy((feats[train_m] - mean) / std)
    ytr = torch.from_numpy(y[train_m]).unsqueeze(1)
    xte = torch.from_numpy((feats[test_m] - mean) / std)
    yte = torch.from_numpy(y[test_m]).unsqueeze(1)

    hidden = (32, 16)
    model = build_mlp(FEATURE_DIM, hidden)
    pos = float(ytr.sum())
    pos_weight = torch.tensor([(len(ytr) - pos) / max(pos, 1.0)])
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)

    best_loss, best_state, bad_epochs, history = float("inf"), None, 0, []
    epochs_run = 0
    for _ in range(epochs):
        epochs_run += 1
        model.train()
        perm = torch.randperm(len(xtr))
        for i in range(0, len(xtr), 64):  # mini-batches of 64 frames
            idx = perm[i : i + 64]
            opt.zero_grad()
            loss = loss_fn(model(xtr[idx]), ytr[idx])
            loss.backward()  # backpropagation: gradients of the loss w.r.t. every weight
            opt.step()  # Adam nudges weights against the gradient
        model.eval()
        with torch.no_grad():
            val_loss = float(loss_fn(model(xte), yte))
        history.append(round(val_loss, 4))
        if val_loss < best_loss - 1e-4:
            best_loss, best_state, bad_epochs = val_loss, copy.deepcopy(model.state_dict()), 0
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                break

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        prob = torch.sigmoid(model(xte)).squeeze(1).numpy()
    metrics = _metrics(y[test_m].astype(int), prob) | {
        "epochs": epochs_run,
        "train_frames": int(train_m.sum()),
        "test_groups": sorted({str(g) for g in groups[test_m]}),
    }
    checkpoint = {
        "state_dict": model.state_dict(),
        "input_dim": FEATURE_DIM,
        "hidden": list(hidden),
        "mean": mean.tolist(),
        "std": std.tolist(),
        "feature_version": FEATURE_VERSION,
        "metrics": metrics,
        "val_loss_history": history,
    }
    return TrainResult(checkpoint=checkpoint, metrics=metrics)
