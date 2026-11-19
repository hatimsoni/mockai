import joblib
from fastapi.testclient import TestClient

from app import quality
from app.agents.evaluator import heuristic_evaluation
from app.agents.state import TurnIn
from app.main import app

client = TestClient(app)


def _train_tiny_model(path):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    good = "I reduced latency from 800 ms to 120 ms by adding a Redis cache, as a result costs fell 30%"
    bad = "um I guess I did some stuff and it was okay"
    texts = [quality.model_input("Q", good)] * 10 + [quality.model_input("Q", bad)] * 10
    labels = [5] * 10 + [1] * 10
    pipe = Pipeline([("tfidf", TfidfVectorizer()), ("clf", LogisticRegression())]).fit(texts, labels)
    joblib.dump(pipe, path)
    return good, bad


def _use_models_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))
    from app.config import get_settings

    get_settings.cache_clear()
    quality.reset()


def test_quality_endpoint_with_model(monkeypatch, tmp_path):
    _use_models_dir(monkeypatch, tmp_path)
    good, bad = _train_tiny_model(tmp_path / quality.MODEL_FILE)
    hi = client.post("/ml/quality", json={"question": "Q", "answer": good}).json()
    lo = client.post("/ml/quality", json={"question": "Q", "answer": bad}).json()
    quality.reset()
    assert hi["available"] and hi["label"] == 5 and hi["score"] > lo["score"]
    assert abs(sum(hi["probabilities"].values()) - 1) < 0.01


def test_quality_endpoint_without_model(monkeypatch, tmp_path):
    _use_models_dir(monkeypatch, tmp_path)
    res = client.post("/ml/quality", json={"question": "Q", "answer": "hello there"}).json()
    quality.reset()
    assert res == {"available": False, "score": None, "label": None, "probabilities": None, "finetuned_score": None}


def test_evaluator_fallback_uses_baseline(monkeypatch, tmp_path):
    _use_models_dir(monkeypatch, tmp_path)
    good, _ = _train_tiny_model(tmp_path / quality.MODEL_FILE)
    e = heuristic_evaluation(TurnIn(index=0, question="Q", transcript=good), "LLM down")
    quality.reset()
    assert e.fallback and e.relevance >= 4
