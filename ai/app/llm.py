"""LLM access + a robust "ask for JSON" helper.

Concept: we talk to Ollama through its OpenAI-compatible endpoint, so the exact same
code also works with any hosted OpenAI-compatible provider (set LLM_BASE_URL).

LLMs are not guaranteed to return valid JSON. `invoke_json` therefore:
  1. asks for JSON (and enables the provider's JSON mode),
  2. extracts the JSON object from the reply (models sometimes wrap it in ```json fences),
  3. validates it against a Pydantic schema (types, ranges, required fields),
  4. on failure, shows the model its own reply + the validation error and asks again.
"""
from __future__ import annotations

import json
import logging
import re
from typing import TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, ValidationError

from app.config import get_settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

# Tests (and notebooks) can inject a fake model here instead of calling Ollama.
_llm_override: BaseChatModel | None = None


def set_llm_override(llm: BaseChatModel | None) -> None:
    global _llm_override
    _llm_override = llm


def get_llm(json_mode: bool = False):
    if _llm_override is not None:
        return _llm_override
    from langchain_openai import ChatOpenAI  # imported lazily: keeps startup fast

    s = get_settings()
    llm = ChatOpenAI(
        base_url=s.llm_base_url,
        api_key=s.llm_api_key,
        model=s.llm_model,
        temperature=s.llm_temperature,
        timeout=s.llm_timeout_seconds,
        max_retries=1,
    )
    # JSON mode constrains decoding so the model can only emit valid JSON tokens.
    return llm.bind(response_format={"type": "json_object"}) if json_mode else llm


class LLMOutputError(RuntimeError):
    """The model never produced output matching the schema."""


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in reply")
    return json.loads(text[start : end + 1])


def invoke_json(messages: list[BaseMessage], schema: type[T], retries: int = 2, llm=None) -> T:
    llm = llm or get_llm(json_mode=True)
    history = list(messages)
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        reply = llm.invoke(history)
        raw = reply.content if isinstance(reply.content, str) else str(reply.content)
        try:
            return schema.model_validate(extract_json(raw))
        except (ValueError, ValidationError) as err:
            last_error = err
            log.warning("invalid LLM JSON (attempt %d/%d): %s", attempt + 1, retries + 1, err)
            history += [
                AIMessage(content=raw),
                HumanMessage(
                    content=f"That reply was invalid: {err}\n"
                    "Reply again with ONLY a valid JSON object that matches the requested schema."
                ),
            ]
    raise LLMOutputError(str(last_error))
