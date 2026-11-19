"""Optional: the LoRA fine-tuned Qwen2.5-0.5B scorer, served by Ollama (see phase 7 notebook).

Enabled by SCORER_MODEL=mockai-scorer after `ollama create mockai-scorer -f Modelfile`.
A 0.5B model answers in well under a second on CPU, so it's a cheap third opinion next to the
7B LLM evaluator and the scikit-learn baseline.
"""
from __future__ import annotations

import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_settings
from app.llm import get_llm
from app.scoring_prompt import SYSTEM, USER_TEMPLATE

log = logging.getLogger(__name__)


def score(question: str, answer: str) -> int | None:
    model = get_settings().scorer_model
    if not model or not (answer or "").strip():
        return None
    try:
        llm = get_llm(model=model, temperature=0, max_tokens=2)
        reply = llm.invoke([
            SystemMessage(content=SYSTEM),  # same prompt as training -> no prompt skew
            HumanMessage(content=USER_TEMPLATE.format(question=question, answer=answer)),
        ]).content
    except Exception as err:  # noqa: BLE001 - optional component
        log.warning("fine-tuned scorer unavailable: %s", err)
        return None
    m = re.search(r"[1-5]", str(reply))
    return int(m.group()) if m else None
