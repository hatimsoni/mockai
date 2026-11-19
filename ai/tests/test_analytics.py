from fastapi.testclient import TestClient

from app.analytics import SessionData, answers_frame, progress
from app.main import app

client = TestClient(app)


def turn(score, topic="apis", wpm=130, fpm=3.0, fillers=None, att=0.9, depth=None):
    return {
        "kind": "main", "topic": topic, "score": score, "baseline_score": score - 0.2, "duration_sec": 60,
        "evaluation": {"relevance": 4, "depth": depth if depth is not None else round(score), "clarity": 4, "star": 3},
        "nlp": {"wpm": wpm, "fillers_per_min": fpm, "keyword_coverage": 0.3, "fillers": fillers or {"um": 2}},
        "attention": {"samples": 50, "attentive_ratio": att},
    }


def session(i, date, scores, **kw):
    return {"id": f"s{i}", "created_at": date, "job_title": "Backend", "status": "COMPLETED",
            "overall_score": sum(scores) / len(scores), "turns": [turn(s, **kw) for s in scores]}


SESSIONS = [
    session(2, "2026-11-10T10:00:00Z", [3.0, 4.0]),           # out of order on purpose
    session(1, "2026-11-01T10:00:00Z", [2.0, 2.0], topic="sql", fillers={"um": 5, "like": 1}),
    session(3, "2026-11-15T10:00:00Z", [4.0, 5.0]),
]


def test_answers_frame_skips_unanswered():
    s = SessionData(**session(9, "2026-11-01T00:00:00Z", [3.0]))
    s.turns.append(s.turns[0].model_copy(update={"score": None}))
    assert len(answers_frame([s])) == 1


def test_progress_timeline_sorted_with_rolling_mean():
    out = progress([SessionData(**s) for s in SESSIONS])
    tl = out["timeline"]
    assert [t["session_id"] for t in tl] == ["s1", "s2", "s3"]
    assert [t["overall"] for t in tl] == [2.0, 3.5, 4.5]
    assert tl[1]["rolling_overall"] == 2.75 and tl[2]["rolling_overall"] == 3.33
    assert out["summary"]["improvement"] == 2.5
    assert out["summary"]["total_answers"] == 6 and out["summary"]["practice_minutes"] == 6.0


def test_topics_weakest_first_and_filler_totals():
    out = progress([SessionData(**s) for s in SESSIONS])
    assert out["topics"][0] == {"topic": "sql", "avg_score": 2.0, "answers": 2}
    assert out["fillers"] == {"um": 18, "like": 2}


def test_recommendations_flag_problems():
    bad = [session(1, "2026-11-01T00:00:00Z", [2.0], wpm=190, fpm=9, att=0.4, depth=1)]
    tips = " ".join(progress([SessionData(**s) for s in bad])["recommendations"])
    assert "depth" in tips and "filler" in tips and "fast" in tips and "Eye contact" in tips


def test_empty_history():
    out = progress([])
    assert out["timeline"] == [] and out["summary"]["total_answers"] == 0


def test_endpoint():
    res = client.post("/analytics/progress", json={"sessions": SESSIONS})
    assert res.status_code == 200, res.text
    assert len(res.json()["timeline"]) == 3
