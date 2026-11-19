import pytest
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.llm import LLMOutputError, extract_json, invoke_json


class Score(BaseModel):
    score: int = Field(ge=1, le=5)


def test_extract_json_strips_fences_and_prose():
    assert extract_json('Sure!\n```json\n{"score": 3}\n```') == {"score": 3}


def test_invoke_json_retries_until_valid(fake_llm):
    model = fake_llm(['{"score": 9}', "oops", '{"score": 4}'])
    result = invoke_json([HumanMessage(content="rate")], Score, retries=2, llm=model)
    assert result.score == 4


def test_invoke_json_gives_up(fake_llm):
    model = fake_llm(["bad", "bad"])
    with pytest.raises(LLMOutputError):
        invoke_json([HumanMessage(content="rate")], Score, retries=1, llm=model)
