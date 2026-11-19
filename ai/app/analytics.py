"""Progress dashboard analytics with Pandas.

Input: every session of one user with its answered turns (sent by the API).
Output: chart-ready JSON — KPIs, a per-session timeline with a rolling average, averages per
rubric criterion, weakest topics, filler-word totals, and rule-based recommendations.

Concepts:
- Long ("tidy") table: one row per answer, columns for every metric. Every question becomes a
  `groupby` + aggregation instead of nested loops.
- Rolling mean: average of the last k sessions — smooths noisy single interviews so the trend is visible.
"""
from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

CRITERIA = ["relevance", "depth", "clarity", "star"]


class TurnData(BaseModel):
    kind: str = "main"
    topic: str | None = None
    score: float | None = None
    baseline_score: float | None = None
    duration_sec: float | None = None
    evaluation: dict[str, Any] | None = None
    nlp: dict[str, Any] | None = None
    attention: dict[str, Any] | None = None


class SessionData(BaseModel):
    id: str
    created_at: str
    job_title: str
    status: str
    overall_score: float | None = None
    turns: list[TurnData] = Field(default_factory=list)


def answers_frame(sessions: list[SessionData]) -> pd.DataFrame:
    """Flatten sessions -> one row per answered turn."""
    rows = []
    for s in sessions:
        for t in s.turns:
            if t.score is None:
                continue
            ev, nlp, att = t.evaluation or {}, t.nlp or {}, t.attention or {}
            rows.append({
                "session_id": s.id,
                "created_at": pd.to_datetime(s.created_at, utc=True),
                "job_title": s.job_title,
                "topic": (t.topic or "general").lower(),
                "kind": t.kind,
                "score": t.score,
                "baseline_score": t.baseline_score,
                "duration_sec": t.duration_sec,
                **{c: ev.get(c) for c in CRITERIA},
                "wpm": nlp.get("wpm"),
                "fillers_per_min": nlp.get("fillers_per_min"),
                "keyword_coverage": nlp.get("keyword_coverage"),
                "attentive_ratio": att.get("attentive_ratio") if att.get("samples") else None,
                "fillers": nlp.get("fillers") or {},
            })
    return pd.DataFrame(rows)


def _clean(value):
    """NaN -> None, numpy numbers -> rounded Python floats (JSON-safe)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return round(float(value), 2)


def recommendations(df: pd.DataFrame) -> list[str]:
    tips = []
    crit = df[CRITERIA].mean()
    if crit.notna().any():
        weakest = crit.idxmin()
        advice = {
            "relevance": "answer the exact question first, in one sentence, then add detail",
            "depth": "name the technologies, the decision you made, the trade-off, and a number",
            "clarity": "use a 3-part structure and stop after the result instead of trailing off",
            "star": "practise Situation → Task → Action → Result; most answers skip the Result",
        }[weakest]
        tips.append(f"Your weakest area is {weakest} ({crit[weakest]:.1f}/5): {advice}.")
    fpm = df["fillers_per_min"].dropna()
    if len(fpm) and fpm.mean() > 6:
        tips.append(f"You average {fpm.mean():.1f} filler words per minute — pause silently instead of saying 'um'.")
    wpm = df["wpm"].dropna()
    if len(wpm) and wpm.mean() > 170:
        tips.append(f"You speak fast ({wpm.mean():.0f} wpm). Aim for 130–160 so interviewers can follow.")
    elif len(wpm) and wpm.mean() < 100:
        tips.append(f"Your pace is slow ({wpm.mean():.0f} wpm). Prepare 2–3 stories so answers flow.")
    att = df["attentive_ratio"].dropna()
    if len(att) and att.mean() < 0.7:
        tips.append(f"Eye contact was {att.mean():.0%} of the time — keep notes near the camera.")
    kw = df["keyword_coverage"].dropna()
    if len(kw) and kw.mean() < 0.15:
        tips.append("Use the job description's vocabulary more — mention the exact tools and skills it lists.")
    return tips or ["Solid all round — increase difficulty with more technical questions or a new job description."]


def progress(sessions: list[SessionData]) -> dict:
    df = answers_frame(sessions)
    completed = [s for s in sessions if s.status == "COMPLETED" and s.overall_score is not None]
    if df.empty:
        return {"summary": {"total_sessions": len(sessions), "completed_sessions": len(completed), "total_answers": 0},
                "timeline": [], "criteria": {}, "topics": [], "fillers": {}, "recommendations": []}

    # --- one row per session, in time order ---
    per_session = (
        df.groupby(["session_id", "created_at", "job_title"], as_index=False)
        .agg(overall=("score", "mean"), answers=("score", "size"), baseline=("baseline_score", "mean"),
             **{c: (c, "mean") for c in CRITERIA},
             wpm=("wpm", "mean"), fillers_per_min=("fillers_per_min", "mean"),
             keyword_coverage=("keyword_coverage", "mean"), attentive_ratio=("attentive_ratio", "mean"))
        .sort_values("created_at")
        .reset_index(drop=True)
    )
    per_session["rolling_overall"] = per_session["overall"].rolling(3, min_periods=1).mean()
    timeline = [
        {"session_id": r.session_id, "date": r.created_at.strftime("%Y-%m-%d"), "job_title": r.job_title,
         **{k: _clean(getattr(r, k)) for k in ["overall", "rolling_overall", "baseline", *CRITERIA, "wpm",
                                              "fillers_per_min", "keyword_coverage", "attentive_ratio"]},
         "answers": int(r.answers)}
        for r in per_session.itertuples()
    ]

    # --- topics: weakest first, at least 1 answer ---
    topics = (
        df.groupby("topic").agg(avg_score=("score", "mean"), answers=("score", "size"))
        .sort_values("avg_score").head(8).reset_index()
    )

    # --- filler totals: explode the per-answer dicts into a Series and sum by word ---
    filler_series = pd.Series(
        [count for d in df["fillers"] for count in d.values()],
        index=[word for d in df["fillers"] for word in d],
        dtype="float64",
    )
    fillers = filler_series.groupby(level=0).sum().sort_values(ascending=False).astype(int).to_dict()

    first, last = per_session["overall"].iloc[0], per_session["overall"].iloc[-1]
    summary = {
        "total_sessions": len(sessions),
        "completed_sessions": len(completed),
        "total_answers": int(len(df)),
        "avg_score": _clean(df["score"].mean()),
        "best_session_score": _clean(per_session["overall"].max()),
        "latest_score": _clean(last),
        "improvement": _clean(last - first) if len(per_session) > 1 else None,
        "practice_minutes": _clean(df["duration_sec"].fillna(0).sum() / 60),
    }
    return {
        "summary": summary,
        "timeline": timeline,
        "criteria": {c: _clean(df[c].mean()) for c in CRITERIA},
        "topics": [{"topic": r.topic, "avg_score": _clean(r.avg_score), "answers": int(r.answers)}
                   for r in topics.itertuples()],
        "fillers": fillers,
        "recommendations": recommendations(df),
    }
