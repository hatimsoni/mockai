"""Landmarks -> model features. Shared by training (ml/vision) and serving (this service).

Privacy by design: the browser runs MediaPipe FaceLandmarker locally and sends us only 45
numbers per frame — 15 key points x (x, y, z) — never images or video.

MediaPipe FaceMesh gives 478 points (468 face + 10 iris). We keep the 15 that matter for
"where is the person looking". KEY_LANDMARKS must match frontend/src/lib/landmarks.ts
exactly (a test enforces this) — otherwise training and serving would disagree
("train/serve skew"), the classic silent ML bug.
"""
from __future__ import annotations

import numpy as np

# (name, MediaPipe index) — order matters, it defines the feature vector layout.
KEY_LANDMARKS: list[tuple[str, int]] = [
    ("nose_tip", 1),
    ("chin", 152),
    ("forehead", 10),
    ("left_eye_outer", 33),
    ("left_eye_inner", 133),
    ("left_eye_top", 159),
    ("left_eye_bottom", 145),
    ("right_eye_outer", 263),
    ("right_eye_inner", 362),
    ("right_eye_top", 386),
    ("right_eye_bottom", 374),
    ("left_iris", 468),
    ("right_iris", 473),
    ("left_cheek", 234),
    ("right_cheek", 454),
]
NAMES = [n for n, _ in KEY_LANDMARKS]
IDX = {n: i for i, n in enumerate(NAMES)}
N_POINTS = len(KEY_LANDMARKS)
RAW_DIM = N_POINTS * 3  # 45
ENGINEERED = ["yaw", "pitch", "left_iris_h", "right_iris_h", "left_iris_v", "right_iris_v"]
FEATURE_DIM = RAW_DIM + len(ENGINEERED)  # 51
FEATURE_VERSION = 1


def _ratio(value: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    span = hi - lo
    return np.where(np.abs(span) > 1e-6, (value - lo) / np.where(np.abs(span) > 1e-6, span, 1), 0.5)


def engineered_features(pts: np.ndarray) -> np.ndarray:
    """Hand-crafted head-pose / gaze proxies. pts: (n, 15, 3) in image coordinates (0-1)."""
    p = lambda name: pts[:, IDX[name], :]  # noqa: E731
    nose, chin, forehead = p("nose_tip"), p("chin"), p("forehead")
    lcheek, rcheek = p("left_cheek"), p("right_cheek")
    # yaw: is the nose centred between the cheeks? (head turned left/right) -> ~0 when facing camera
    yaw = _ratio(nose[:, 0], lcheek[:, 0], rcheek[:, 0]) - 0.5
    # pitch: nose height between forehead and chin (head tilted up/down)
    pitch = _ratio(nose[:, 1], forehead[:, 1], chin[:, 1]) - 0.5
    # iris position inside each eye: 0.5 = looking straight
    l_h = _ratio(p("left_iris")[:, 0], p("left_eye_outer")[:, 0], p("left_eye_inner")[:, 0])
    r_h = _ratio(p("right_iris")[:, 0], p("right_eye_inner")[:, 0], p("right_eye_outer")[:, 0])
    l_v = _ratio(p("left_iris")[:, 1], p("left_eye_top")[:, 1], p("left_eye_bottom")[:, 1])
    r_v = _ratio(p("right_iris")[:, 1], p("right_eye_top")[:, 1], p("right_eye_bottom")[:, 1])
    return np.stack([yaw, pitch, l_h, r_h, l_v, r_v], axis=1)


def to_features(frames: np.ndarray | list) -> np.ndarray:
    """(n, 45) raw landmarks -> (n, 51) features.

    1. Translate so the nose tip is the origin (position in the frame doesn't matter).
    2. Scale by the distance between the outer eye corners (distance to camera doesn't matter).
    3. Append engineered yaw / pitch / iris ratios.
    """
    x = np.asarray(frames, dtype=np.float32)
    if x.ndim != 2 or x.shape[1] != RAW_DIM:
        raise ValueError(f"expected shape (n, {RAW_DIM}), got {x.shape}")
    pts = x.reshape(-1, N_POINTS, 3)
    eng = engineered_features(pts)
    centred = pts - pts[:, IDX["nose_tip"] : IDX["nose_tip"] + 1, :]
    eye_dist = np.linalg.norm(pts[:, IDX["left_eye_outer"], :2] - pts[:, IDX["right_eye_outer"], :2], axis=1)
    scale = np.maximum(eye_dist, 1e-6)[:, None, None]
    normalized = (centred / scale).reshape(-1, RAW_DIM)
    return np.concatenate([normalized, eng], axis=1).astype(np.float32)


def heuristic_attentive_prob(features: np.ndarray) -> np.ndarray:
    """Rule-based score used until a trained model exists. 1 = looking at the screen."""
    yaw, pitch, lh, rh, lv, rv = (features[:, RAW_DIM + i] for i in range(6))
    iris_h = (lh + rh) / 2
    iris_v = (lv + rv) / 2
    # penalties grow as head turns or eyes move away from centre
    penalty = (
        np.clip((np.abs(yaw) - 0.10) / 0.15, 0, 1)
        + np.clip((np.abs(pitch) - 0.12) / 0.15, 0, 1)
        + np.clip((np.abs(iris_h - 0.5) - 0.12) / 0.12, 0, 1)
        + np.clip((np.abs(iris_v - 0.5) - 0.2) / 0.2, 0, 1)
    )
    return np.clip(1 - penalty, 0, 1).astype(np.float32)
