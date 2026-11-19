import re
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.vision import model as vision_model
from app.vision.features import FEATURE_DIM, KEY_LANDMARKS, RAW_DIM, heuristic_attentive_prob, to_features
from app.vision.synthetic import make_dataset, make_frame
from app.vision.training import group_split, train_attention

client = TestClient(app)
REPO = Path(__file__).resolve().parents[2]


def test_landmark_lists_match_frontend():
    """Train/serve skew guard: the browser must send exactly the points the model expects."""
    ts = (REPO / "frontend" / "src" / "lib" / "landmarks.ts").read_text(encoding="utf-8")
    frontend = [(n, int(i)) for n, i in re.findall(r'\["(\w+)",\s*(\d+)\]', ts)]
    assert frontend == KEY_LANDMARKS


def test_features_are_translation_and_scale_invariant():
    a = to_features([make_frame()])
    b = to_features([make_frame(shift=(0.1, -0.05), scale=1.3)])
    assert a.shape == (1, FEATURE_DIM)
    np.testing.assert_allclose(a, b, atol=1e-4)


def test_features_reject_wrong_shape():
    with pytest.raises(ValueError):
        to_features([[0.0] * 10])


def test_heuristic_separates_obvious_cases():
    straight = heuristic_attentive_prob(to_features([make_frame()]))[0]
    turned = heuristic_attentive_prob(to_features([make_frame(yaw=1.5)]))[0]
    looking_down = heuristic_attentive_prob(to_features([make_frame(pitch=1.5)]))[0]
    assert straight > 0.9 and turned < 0.5 and looking_down < 0.5


def test_group_split_keeps_recordings_together():
    groups = np.array(["a"] * 5 + ["b"] * 5 + ["c"] * 5 + ["d"] * 5 + ["e"] * 5)
    train, test = group_split(groups)
    assert set(groups[train]).isdisjoint(set(groups[test]))
    assert test.sum() == 5


def test_training_learns_synthetic_task_and_checkpoint_loads(tmp_path):
    frames, labels, groups = make_dataset(n_per_class=200, n_groups=5)
    result = train_attention(frames, labels, groups, epochs=60, patience=15)
    assert result.metrics["accuracy"] > 0.9, result.metrics

    import torch

    path = tmp_path / "attention_mlp.pt"
    torch.save(result.checkpoint, path)
    predictor = vision_model.AttentionPredictor(path)
    assert predictor.kind == "mlp"
    probs = predictor.predict_proba([make_frame().tolist(), make_frame(yaw=1.5).tolist()])
    assert probs[0] > 0.5 > probs[1]


def test_predict_endpoint_uses_heuristic_without_model(monkeypatch, tmp_path):
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))  # empty dir -> no trained model
    from app.config import get_settings

    get_settings.cache_clear()
    vision_model.reset_predictor()
    res = client.post("/vision/predict", json={"frames": [make_frame().tolist(), make_frame(yaw=1.5).tolist()]})
    vision_model.reset_predictor()
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["model"] == "heuristic"
    assert body["attentive"] == [True, False]


def test_predict_endpoint_validates_frame_size():
    res = client.post("/vision/predict", json={"frames": [[0.1] * (RAW_DIM - 1)]})
    assert res.status_code == 422
