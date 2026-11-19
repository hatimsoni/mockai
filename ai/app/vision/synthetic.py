"""Synthetic landmark frames — ONLY for tests and pipeline demos, never for the shipped model.

Builds a rough frontal face in normalized image coordinates and simulates head turns and
eye movements. Real training data must come from a webcam (see ml/vision/README.md).
"""
from __future__ import annotations

import numpy as np

from app.vision.features import IDX, N_POINTS

# Rough frontal face template (x, y, z), image coords 0..1, face centred at (0.5, 0.5).
TEMPLATE = {
    "nose_tip": (0.50, 0.55, -0.05),
    "chin": (0.50, 0.75, 0.0),
    "forehead": (0.50, 0.30, 0.0),
    "left_eye_outer": (0.40, 0.45, 0.0),
    "left_eye_inner": (0.46, 0.45, 0.0),
    "left_eye_top": (0.43, 0.435, 0.0),
    "left_eye_bottom": (0.43, 0.465, 0.0),
    "right_eye_outer": (0.60, 0.45, 0.0),
    "right_eye_inner": (0.54, 0.45, 0.0),
    "right_eye_top": (0.57, 0.435, 0.0),
    "right_eye_bottom": (0.57, 0.465, 0.0),
    "left_iris": (0.43, 0.45, 0.0),
    "right_iris": (0.57, 0.45, 0.0),
    "left_cheek": (0.33, 0.55, 0.05),
    "right_cheek": (0.67, 0.55, 0.05),
}


def make_frame(yaw: float = 0.0, pitch: float = 0.0, gaze_x: float = 0.0, gaze_y: float = 0.0,
               shift=(0.0, 0.0), scale: float = 1.0, rng=None) -> np.ndarray:
    pts = np.zeros((N_POINTS, 3), dtype=np.float32)
    for name, (x, y, z) in TEMPLATE.items():
        pts[IDX[name]] = (x, y, z)
    # head turn: nose (closest to camera) moves most horizontally, cheeks move less
    pts[IDX["nose_tip"], 0] += yaw * 0.12
    pts[IDX["nose_tip"], 1] += pitch * 0.12
    for eye in ("left_iris", "right_iris"):
        pts[IDX[eye], 0] += gaze_x * 0.025 + yaw * 0.01
        pts[IDX[eye], 1] += gaze_y * 0.012
    # camera distance / position
    pts[:, :2] = (pts[:, :2] - 0.5) * scale + 0.5 + np.asarray(shift, dtype=np.float32)
    pts[:, 2] *= scale  # MediaPipe z uses roughly the same scale as x, so it grows with face size
    if rng is not None:
        pts += rng.normal(0, 0.002, pts.shape).astype(np.float32)
    return pts.reshape(-1)


def make_dataset(n_per_class: int = 300, n_groups: int = 6, seed: int = 0):
    """Returns frames (n, 45), labels (1 = attentive), groups (fake recording ids)."""
    rng = np.random.default_rng(seed)
    frames, labels, groups = [], [], []
    for label in (1, 0):
        for i in range(n_per_class):
            common = {"shift": rng.uniform(-0.08, 0.08, 2), "scale": rng.uniform(0.7, 1.3), "rng": rng}
            if label == 1:
                f = make_frame(yaw=rng.normal(0, 0.15), pitch=rng.normal(0, 0.15),
                               gaze_x=rng.normal(0, 0.3), gaze_y=rng.normal(0, 0.3), **common)
            else:
                side = rng.choice([-1, 1])
                mode = rng.integers(0, 3)
                yaw = side * rng.uniform(0.8, 1.6) if mode == 0 else rng.normal(0, 0.15)
                pitch = rng.uniform(0.9, 1.6) if mode == 1 else rng.normal(0, 0.15)  # looking down (notes/phone)
                gaze = side * rng.uniform(1.0, 1.8) if mode == 2 else rng.normal(0, 0.3)
                f = make_frame(yaw=yaw, pitch=pitch, gaze_x=gaze, **common)
            frames.append(f)
            labels.append(label)
            groups.append(f"rec{i % n_groups}")
    return np.stack(frames), np.array(labels), np.array(groups)
