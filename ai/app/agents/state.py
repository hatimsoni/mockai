"""Shared state passed between the agents in the LangGraph graph.

Concept — LangGraph: you describe a workflow as a graph. Nodes are functions (here: our
three agents) that read the shared state and return *partial updates*; edges decide which
node runs next, possibly based on the state (conditional edges). Compared with one giant
prompt, each agent has one job, its own prompt and its own validation, and the control flow
(when to follow up, when to write the report) is explicit, testable Python.

The AI service is stateless: the API sends the whole interview so far on every call.
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class TurnIn(BaseModel):
    """One question/answer as stored by the API."""

    index: int
    question: str
    kind: Literal["main", "followup"] = "main"
    topic: str | None = None
    transcript: str | None = None
    duration_sec: float | None = None
    evaluation: dict[str, Any] | None = None
    nlp: dict[str, Any] | None = None
    attention: dict[str, Any] | None = None


class PlanItem(BaseModel):
    question: str
    topic: str = "general"
    type: str = "technical"
    sources: list[dict[str, Any]] = Field(default_factory=list)


class NextQuestion(BaseModel):
    question: str
    kind: Literal["main", "followup"]
    topic: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)


class InterviewState(TypedDict, total=False):
    # --- input ---
    session_id: str
    job_title: str
    plan: list[PlanItem]
    turns: list[TurnIn]
    finish: bool
    max_followups: int
    # --- output (filled by agents) ---
    evaluation: dict[str, Any] | None
    next_question: NextQuestion | None
    done: bool
    report: dict[str, Any] | None
