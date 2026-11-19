import json
from pathlib import Path

from app import finetuned
from app.config import get_settings
from app.scoring_prompt import SYSTEM, USER_TEMPLATE

NOTEBOOK = Path(__file__).resolve().parents[2] / "ml" / "finetune" / "lora_qwen_scoring.ipynb"


def test_notebook_uses_the_serving_prompt():
    """Prompt-skew guard: training prompt (notebook) == serving prompt (scoring_prompt.py)."""
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    source = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    assert repr(SYSTEM) in source
    assert USER_TEMPLATE in source


def test_scorer_disabled_by_default():
    assert finetuned.score("Q", "an answer") is None


def test_scorer_parses_digit(fake_llm, monkeypatch):
    monkeypatch.setenv("SCORER_MODEL", "mockai-scorer")
    get_settings.cache_clear()
    fake_llm(["4"])
    assert finetuned.score("Q", "I cut latency by 80%") == 4
    fake_llm(["no idea"])
    assert finetuned.score("Q", "x") is None
