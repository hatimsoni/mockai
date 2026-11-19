"""RAG question planning: retrieve the right chunks, then let the LLM write questions.

Retrieval-Augmented Generation (RAG) = instead of asking the LLM "write interview
questions" (generic, hallucination-prone), we first *retrieve* the specific JD
requirements and the resume passages that match them, put those passages in the prompt
with ids like [J1] / [R3], and require each question to cite the ids it used.
Citations are mapped back to the real text so the UI can show *why* a question was asked.
"""
from __future__ import annotations

import logging
from typing import Literal

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.llm import LLMOutputError, invoke_json
from app.rag.store import all_chunks, retrieve

log = logging.getLogger(__name__)

QuestionType = Literal["technical", "behavioral", "resume"]


# ---- what we ask the LLM to return (validated) ----
class PlannedQuestion(BaseModel):
    question: str = Field(min_length=10)
    topic: str = Field(min_length=2, max_length=80)
    type: QuestionType = "technical"
    source_ids: list[str] = Field(default_factory=list)


class QuestionPlan(BaseModel):
    questions: list[PlannedQuestion] = Field(min_length=1)


# ---- what we return to the API ----
class Source(BaseModel):
    id: str
    source: str  # "resume" | "jd"
    text: str


class Question(BaseModel):
    question: str
    topic: str
    type: QuestionType
    sources: list[Source] = Field(default_factory=list)


SYSTEM = """You are an experienced technical interviewer preparing a mock interview.
You write questions that are specific to the candidate's resume and the job description.
Always reply with a single JSON object and nothing else."""

PROMPT = """Job title: {job_title}

JOB DESCRIPTION EXCERPTS:
{jd_context}

MATCHING RESUME EXCERPTS:
{resume_context}

Write exactly {n} interview questions for this candidate.
Rules:
- Mix: about 60% technical (skills the job needs), 20% resume deep-dives (a project or
  role they listed), 20% behavioral (teamwork, conflict, failure — STAR-style).
- Each question must be answerable in 1-3 minutes of speaking. One question per item.
- Refer to concrete things from the excerpts (technologies, projects, responsibilities).
- "source_ids" lists the excerpt ids you used, e.g. ["J1", "R2"].

Reply as JSON:
{{"questions": [{{"question": "...", "topic": "short topic", "type": "technical|resume|behavioral", "source_ids": ["J1"]}}]}}"""


def _number(docs: list[Document], prefix: str) -> dict[str, Document]:
    return {f"{prefix}{i + 1}": d for i, d in enumerate(docs)}


def _format(numbered: dict[str, Document]) -> str:
    return "\n".join(f"[{k}] {d.page_content}" for k, d in numbered.items()) or "(none)"


def gather_context(session_id: str, max_jd: int = 6, max_resume: int = 8) -> tuple[dict, dict]:
    """JD chunks = the requirements. For each requirement, find the closest resume chunks."""
    jd_docs = all_chunks(session_id, "jd")[:max_jd]
    resume_docs: list[Document] = []
    seen: set[str] = set()
    for jd in jd_docs:
        for doc in retrieve(session_id, jd.page_content, k=2, source="resume"):
            key = doc.page_content
            if key not in seen:
                seen.add(key)
                resume_docs.append(doc)
    if not resume_docs:  # empty JD? fall back to the start of the resume
        resume_docs = all_chunks(session_id, "resume")
    return _number(jd_docs, "J"), _number(resume_docs[:max_resume], "R")


def fallback_questions(jd: dict[str, Document], n: int) -> list[Question]:
    """Used only if the LLM is unreachable or never returns valid JSON."""
    out = [
        Question(
            question=f"The role mentions: \"{doc.page_content[:160].strip()}\". "
            "Tell me about your experience with this.",
            topic="job requirement",
            type="technical",
            sources=[Source(id=k, source="jd", text=doc.page_content)],
        )
        for k, doc in jd.items()
    ]
    out.append(
        Question(
            question="Tell me about a time you faced a difficult problem at work. What did you do?",
            topic="problem solving",
            type="behavioral",
        )
    )
    return out[:n]


def plan_questions(session_id: str, job_title: str, n: int = 5) -> list[Question]:
    jd, resume = gather_context(session_id)
    lookup = {**jd, **resume}
    messages = [
        SystemMessage(content=SYSTEM),
        HumanMessage(
            content=PROMPT.format(
                job_title=job_title, jd_context=_format(jd), resume_context=_format(resume), n=n
            )
        ),
    ]
    try:
        plan = invoke_json(messages, QuestionPlan)
    except (LLMOutputError, Exception) as err:  # noqa: BLE001 - network errors too
        log.error("question planning failed, using fallback: %s", err)
        return fallback_questions(jd, n)

    questions = []
    for q in plan.questions[:n]:
        sources = [
            Source(id=sid, source=lookup[sid].metadata["source"], text=lookup[sid].page_content)
            for sid in q.source_ids
            if sid in lookup  # drop hallucinated ids
        ]
        questions.append(Question(question=q.question, topic=q.topic, type=q.type, sources=sources))
    return questions
