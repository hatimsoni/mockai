"""Interviewer agent: decides what to ask next.

Decision policy (explicit and testable):
  1. If the Evaluator flagged the last *main* answer as needing a follow-up, and we still
     have follow-up budget, the LLM writes one probing question — grounded in the candidate's
     answer and the most relevant resume chunks (RAG again).
  2. Otherwise ask the next unasked question from the RAG question plan.
  3. If the plan is exhausted, the interview is done.
Only step 1 calls the LLM, which keeps the loop fast on a CPU.
"""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.state import InterviewState, NextQuestion
from app.llm import invoke_json
from app.rag.store import retrieve

log = logging.getLogger(__name__)

DEFAULT_MAX_FOLLOWUPS = 2


class FollowUp(BaseModel):
    question: str = Field(min_length=10, max_length=400)


SYSTEM = "You are a friendly but probing technical interviewer. Reply with one JSON object only."

PROMPT = """You asked: {question}
The candidate answered: \"\"\"{answer}\"\"\"
What was missing: {reason}

Relevant lines from the candidate's resume:
{context}

Write ONE short follow-up question (max 2 sentences) that digs into what was missing,
e.g. their specific role, a technical decision and its trade-off, or a measurable result.
Do not repeat the original question. JSON: {{"question": "..."}}"""


def write_follow_up(session_id: str, question: str, answer: str, reason: str) -> NextQuestion:
    try:
        chunks = retrieve(session_id, f"{question} {answer}", k=2, source="resume")
    except Exception:  # noqa: BLE001 - no collection (e.g. tests) -> no context
        chunks = []
    context = "\n".join(f"- {c.page_content}" for c in chunks) or "(none)"
    try:
        fu = invoke_json(
            [
                SystemMessage(content=SYSTEM),
                HumanMessage(
                    content=PROMPT.format(
                        question=question, answer=answer[:2500], reason=reason or "more specifics", context=context
                    )
                ),
            ],
            FollowUp,
        )
        text = fu.question
    except Exception as err:  # noqa: BLE001
        log.error("follow-up generation failed, using template: %s", err)
        text = "Can you go one level deeper — what exactly did you do yourself, and what was the measurable result?"
    sources = [{"id": f"R{i + 1}", "source": "resume", "text": c.page_content} for i, c in enumerate(chunks)]
    return NextQuestion(question=text, kind="followup", sources=sources)


def choose_next(state: InterviewState) -> NextQuestion | None:
    turns = state.get("turns", [])
    plan = state.get("plan", [])
    max_followups = state.get("max_followups", DEFAULT_MAX_FOLLOWUPS)

    if turns:
        last = turns[-1]
        ev = last.evaluation or {}
        followups_used = sum(1 for t in turns if t.kind == "followup")
        if (
            last.kind == "main"  # never follow up on a follow-up
            and ev.get("needs_follow_up")
            and not ev.get("fallback")  # don't probe based on a heuristic score
            and followups_used < max_followups
            and last.transcript
        ):
            nq = write_follow_up(state["session_id"], last.question, last.transcript, ev.get("follow_up_reason", ""))
            return nq.model_copy(update={"topic": last.topic})

    main_asked = sum(1 for t in turns if t.kind == "main")
    if main_asked < len(plan):
        item = plan[main_asked]
        return NextQuestion(question=item.question, kind="main", topic=item.topic, sources=item.sources)
    return None


def interviewer_node(state: InterviewState) -> dict:
    nq = choose_next(state)
    return {"next_question": nq, "done": nq is None}
