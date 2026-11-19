"""Coach agent: turns all evaluations into a final, personal feedback report.

Split of work: Python computes every number (averages, best/worst question, speech and
attention stats) so they are exact and reproducible; the LLM only writes the *words*
(summary, priorities, practice plan) from those numbers and the per-answer feedback.
"""
from __future__ import annotations

import json
import logging
from statistics import mean

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.state import InterviewState, TurnIn
from app.llm import invoke_json

log = logging.getLogger(__name__)

CRITERIA = ["relevance", "depth", "clarity", "star"]


class CoachLLM(BaseModel):
    summary: str = Field(min_length=20, max_length=1200)
    top_strengths: list[str] = Field(min_length=1, max_length=4)
    top_improvements: list[str] = Field(min_length=1, max_length=4)
    practice_plan: list[str] = Field(min_length=1, max_length=5)


def _avg(values: list[float]) -> float | None:
    return round(mean(values), 2) if values else None


def compute_scores(turns: list[TurnIn]) -> dict:
    """Deterministic aggregates over answered + evaluated turns."""
    rated = [t for t in turns if t.transcript is not None and t.evaluation]
    evs = [t.evaluation for t in rated]
    nlps = [t.nlp for t in rated if t.nlp]
    atts = [t.attention for t in rated if t.attention and t.attention.get("samples")]
    per_q = [
        {"index": t.index, "question": t.question, "kind": t.kind, "overall": t.evaluation["overall"]}
        for t in rated
    ]
    return {
        "answered": len(rated),
        "overall": _avg([e["overall"] for e in evs]),
        "criteria": {c: _avg([e[c] for e in evs]) for c in CRITERIA},
        "speech": {
            "avg_wpm": _avg([n["wpm"] for n in nlps if n.get("wpm")]),
            "total_fillers": sum(n.get("filler_count", 0) for n in nlps) if nlps else None,
            "fillers_per_min": _avg([n["fillers_per_min"] for n in nlps if "fillers_per_min" in n]),
            "keyword_coverage": _avg([n["keyword_coverage"] for n in nlps if "keyword_coverage" in n]),
        },
        "attention": {"avg_attentive_ratio": _avg([a["attentive_ratio"] for a in atts if "attentive_ratio" in a])},
        "best": max(per_q, key=lambda q: q["overall"]) if per_q else None,
        "weakest": min(per_q, key=lambda q: q["overall"]) if per_q else None,
    }


SYSTEM = """You are an encouraging, honest interview coach. You write concise, specific,
actionable feedback. Reply with one JSON object only."""

PROMPT = """Role: {job_title}

Computed scores (1-5 scale; speech/attention may be null if not measured):
{scores}

Per-question feedback from the evaluator:
{feedback}

Write the candidate's report:
- summary: 3-5 sentences, address the candidate as "you", mention the overall level honestly
- top_strengths: 2-4 specific strengths across answers
- top_improvements: 2-4 highest-impact things to fix, most important first
- practice_plan: 3-5 concrete exercises for the next week (e.g. "Rewrite your X answer using STAR with one metric")

JSON: {{"summary": "...", "top_strengths": ["..."], "top_improvements": ["..."], "practice_plan": ["..."]}}"""


def _feedback_lines(turns: list[TurnIn]) -> str:
    lines = []
    for t in turns:
        if not t.evaluation:
            continue
        e = t.evaluation
        lines.append(
            f"Q{t.index + 1} ({t.kind}) \"{t.question[:120]}\" -> overall {e['overall']}; "
            f"strengths: {'; '.join(e.get('strengths', [])) or '-'}; "
            f"improve: {'; '.join(e.get('improvements', [])) or '-'}"
        )
    return "\n".join(lines)


def fallback_coach(turns: list[TurnIn]) -> CoachLLM:
    strengths = [s for t in turns if t.evaluation for s in t.evaluation.get("strengths", [])][:3]
    improvements = [s for t in turns if t.evaluation for s in t.evaluation.get("improvements", [])][:3]
    return CoachLLM(
        summary="Your answers were scored individually; the AI coach summary was unavailable, "
        "so this report lists the evaluator's main points.",
        top_strengths=strengths or ["You completed the interview."],
        top_improvements=improvements or ["Give more concrete examples with measurable results."],
        practice_plan=[
            "Re-answer your weakest question using Situation, Task, Action, Result.",
            "Add one number (users, latency, %, time saved) to every project story.",
            "Record a 2-minute answer daily and count your filler words.",
        ],
    )


def write_report(turns: list[TurnIn], job_title: str) -> dict:
    scores = compute_scores(turns)
    try:
        coach = invoke_json(
            [
                SystemMessage(content=SYSTEM),
                HumanMessage(
                    content=PROMPT.format(
                        job_title=job_title, scores=json.dumps(scores, indent=1), feedback=_feedback_lines(turns)
                    )
                ),
            ],
            CoachLLM,
        )
        fallback = False
    except Exception as err:  # noqa: BLE001
        log.error("coach failed, using fallback: %s", err)
        coach, fallback = fallback_coach(turns), True
    return {"scores": scores, "coach": coach.model_dump(), "fallback": fallback}


def coach_node(state: InterviewState) -> dict:
    return {"report": write_report(state["turns"], state.get("job_title", "Software Engineer")), "done": True}
