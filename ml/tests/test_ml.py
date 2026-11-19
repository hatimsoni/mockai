"""Tests for the ML scripts (run in CI from the ai/ venv: pytest ../ml/tests)."""
import sys
from pathlib import Path

import pandas as pd

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML / "dataset"))
sys.path.insert(0, str(ML / "classic"))

from build_seed import build, rubric_label  # noqa: E402
from metrics import evaluate  # noqa: E402
from split import make_splits  # noqa: E402


def test_seed_is_deterministic_and_balanced():
    a, b = build(n_per_label=20, seed=1), build(n_per_label=20, seed=1)
    assert [r["answer"] for r in a] == [r["answer"] for r in b]
    labels = pd.Series([r["label"] for r in a]).value_counts()
    assert set(labels.index) == {1, 2, 3, 4, 5} and (labels == 20).all()


def test_rubric_rewards_better_components():
    import random

    rng = random.Random(0)
    weak = sum(rubric_label(0, 0, 1, 2, rng) for _ in range(200)) / 200
    strong = sum(rubric_label(2, 2, 4, 0, rng) for _ in range(200)) / 200
    assert weak < 2 < 4 < strong


def test_non_answers_get_low_labels():
    import random

    rng = random.Random(0)
    assert max(rubric_label(2, 2, 0, 0, rng) for _ in range(100)) <= 2


def test_metrics_known_values():
    m = evaluate([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    assert m["accuracy"] == 1 and m["qwk"] == 1 and m["mae"] == 0
    m = evaluate([1, 2, 3, 4, 5], [2, 3, 4, 5, 5])
    assert m["accuracy"] == 0.2 and m["within_1"] == 1.0 and m["mae"] == 0.8
    assert evaluate([5, 5], [9, -3])["mae"] == 2.0  # predictions are clipped to 1..5


def test_splits_are_stratified_and_disjoint():
    df = pd.DataFrame(build(n_per_label=40, seed=3))
    train, val, test = make_splits(df)
    assert len(train) + len(val) + len(test) == len(df)
    assert set(train["id"]).isdisjoint(test["id"]) and set(val["id"]).isdisjoint(test["id"])
    assert test["label"].value_counts().min() >= 5
