"""Evaluator agent: scores one answer against a rubric, as strict JSON.

Why strict JSON + Pydantic: the scores are stored, averaged and charted. A reply like
"I'd give it a solid 4!" can't be charted. The schema enforces integer scores 1-5, short
lists, and booleans; `invoke_json` retries with the validation error when the model slips.

The overall score is computed here in Python (weighted mean), not by the LLM: LLMs are poor
at arithmetic and it keeps the formula transparent.
"""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.state import InterviewState, TurnIn
from app.llm import invoke_json

log = logging.getLogger(__name__)

WEIGHTS = {"relevance": 0.3, "depth": 0.3, "clarity": 0.2, "star": 0.2}


class StarBreakdown(BaseModel):
    situation: bool = False
    task: bool = False
    action: bool = False
    result: bool = False


class EvaluationLLM(BaseModel):
    """Exactly what the model must return."""

    relevance: int = Field(ge=1, le=5, description="Does it answer the question asked?")
    depth: int = Field(ge=1, le=5, description="Specifics, technical detail, trade-offs, numbers")
    clarity: int = Field(ge=1, le=5, description="Easy to follow, concise, well organised")
    star: int = Field(ge=1, le=5, description="Situation-Task-Action-Result structure")
    star_breakdown: StarBreakdown = Field(default_factory=StarBreakdown)
    strengths: list[str] = Field(default_factory=list, max_length=3)
    improvements: list[str] = Field(default_factory=list, max_length=3)
    needs_follow_up: bool = False
    follow_up_reason: str = ""


class Evaluation(EvaluationLLM):
    overall: float
    fallback: bool = False  # True when produced by the heuristic, not the LLM


SYSTEM = """You are a strict but fair interview evaluator. You score spoken answers that were
transcribed by speech recognition (ignore minor transcription errors and filler words when
judging content). Reply with one JSON object only."""

RUBRIC = """Role: {job_title}
Question ({kind}, topic: {topic}): {question}

Candidate's answer (transcript, {seconds}s):
\"\"\"{answer}\"\"\"
{speech_notes}
Score each criterion from 1 (very poor) to 5 (excellent):
- relevance: answers the actual question
- depth: concrete specifics — technologies, decisions, trade-offs, numbers, their own role
- clarity: easy to follow, logical order, not rambling
- star: Situation, Task, Action, Result present (for technical questions: context -> approach -> outcome)
Also:
- star_breakdown: which STAR parts are present (true/false)
- strengths: up to 3 short, specific points
- improvements: up to 3 short, actionable points
- needs_follow_up: true if the answer is vague or skips something an interviewer would probe
- follow_up_reason: what to probe (empty if none)

JSON format:
{{"relevance": 1-5, "depth": 1-5, "clarity": 1-5, "star": 1-5,
 "star_breakdown": {{"situation": bool, "task": bool, "action": bool, "result": bool}},
 "strengths": ["..."], "improvements": ["..."], "needs_follow_up": bool, "follow_up_reason": "..."}}"""


def overall_score(e: EvaluationLLM) -> float:
    return round(sum(getattr(e, k) * w for k, w in WEIGHTS.items()), 2)


def _speech_notes(turn: TurnIn) -> str:
    if not turn.nlp:
        return ""
    n = turn.nlp
    return (
        f"\nSpeech metrics: {n.get('wpm', '?')} words/min, {n.get('filler_count', '?')} filler words, "
        f"JD keyword coverage {round(100 * n.get('keyword_coverage', 0))}%.\n"
    )


def heuristic_evaluation(turn: TurnIn, reason: str) -> Evaluation:
    """Last-resort scoring when the LLM is unavailable: based on answer length only."""
    words = len((turn.transcript or "").split())
    base = 1 if words < 15 else 2 if words < 50 else 3
    e = EvaluationLLM(
        relevance=base,
        depth=base,
        clarity=base,
        star=max(1, base - 1),
        improvements=[reason],
    )
    return Evaluation(**e.model_dump(), overall=overall_score(e), fallback=True)


def evaluate_turn(turn: TurnIn, job_title: str) -> Evaluation:
    if not turn.transcript or len(turn.transcript.split()) < 3:
        return heuristic_evaluation(turn, "No (or almost no) speech was detected — answer out loud, closer to the mic.")

    messages = [
        SystemMessage(content=SYSTEM),
        HumanMessage(
            content=RUBRIC.format(
                job_title=job_title,
                kind=turn.kind,
                topic=turn.topic or "general",
                question=turn.question,
                seconds=round(turn.duration_sec or 0),
                answer=turn.transcript[:4000],
                speech_notes=_speech_notes(turn),
            )
        ),
    ]
    try:
        e = invoke_json(messages, EvaluationLLM, retries=2)
    except Exception as err:  # noqa: BLE001 - LLM down or never valid
        log.error("evaluator failed, using heuristic: %s", err)
        return heuristic_evaluation(turn, "Automatic AI scoring was unavailable; this score is approximate.")
    return Evaluation(**e.model_dump(), overall=overall_score(e))


def evaluator_node(state: InterviewState) -> dict:
    """Graph node: evaluate the most recent (answered, unevaluated) turn."""
    turns = list(state["turns"])
    last = turns[-1]
    evaluation = evaluate_turn(last, state.get("job_title", "Software Engineer")).model_dump()
    turns[-1] = last.model_copy(update={"evaluation": evaluation})
    return {"turns": turns, "evaluation": evaluation}
