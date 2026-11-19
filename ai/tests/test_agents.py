import json

from fastapi.testclient import TestClient

from app.agents.coach import compute_scores
from app.agents.evaluator import evaluate_turn, overall_score
from app.agents.graph import route_start, run_step
from app.agents.state import PlanItem, TurnIn
from app.main import app

client = TestClient(app)

GOOD_EVAL = {
    "relevance": 5,
    "depth": 4,
    "clarity": 4,
    "star": 3,
    "star_breakdown": {"situation": True, "task": True, "action": True, "result": False},
    "strengths": ["Concrete example"],
    "improvements": ["State the result with a number"],
    "needs_follow_up": False,
    "follow_up_reason": "",
}
VAGUE_EVAL = {**GOOD_EVAL, "depth": 2, "needs_follow_up": True, "follow_up_reason": "no specifics on their role"}
COACH = {
    "summary": "You gave relevant answers with good examples but missed results.",
    "top_strengths": ["Relevant examples"],
    "top_improvements": ["Quantify results"],
    "practice_plan": ["Rewrite one answer with STAR"],
}

PLAN = [
    PlanItem(question="Tell me about your REST API work.", topic="APIs"),
    PlanItem(question="How do you use PostgreSQL indexes?", topic="SQL"),
]
ANSWER = "In my last job I built REST APIs in Express for fifty thousand users and added caching."


def answered(index=0, kind="main", evaluation=None, topic="APIs"):
    return TurnIn(index=index, question=PLAN[0].question, kind=kind, topic=topic, transcript=ANSWER,
                  duration_sec=40, evaluation=evaluation)


# ---------- routing ----------
def test_route_start():
    assert route_start({"turns": [answered()]}) == "evaluator"
    assert route_start({"turns": [answered(evaluation={"overall": 3})], "finish": True}) == "coach"
    assert route_start({"turns": []}) == "interviewer"


# ---------- evaluator ----------
def test_overall_is_weighted_mean():
    from app.agents.evaluator import EvaluationLLM

    e = EvaluationLLM(relevance=5, depth=4, clarity=4, star=3)
    assert overall_score(e) == round(5 * 0.3 + 4 * 0.3 + 4 * 0.2 + 3 * 0.2, 2)


def test_evaluator_retries_then_succeeds(fake_llm):
    fake_llm(['{"relevance": 7}', json.dumps(GOOD_EVAL)])  # first reply out of range
    e = evaluate_turn(answered(), "Backend Engineer")
    assert e.relevance == 5 and not e.fallback and e.overall == 4.1


def test_evaluator_falls_back_when_llm_never_valid(fake_llm):
    fake_llm(["nope", "nope", "nope"])
    e = evaluate_turn(answered(), "Backend Engineer")
    assert e.fallback and 1 <= e.overall <= 5


def test_empty_answer_skips_llm(fake_llm):
    model = fake_llm([])  # would raise if called
    turn = answered().model_copy(update={"transcript": ""})
    e = evaluate_turn(turn, "Dev")
    assert e.fallback and e.overall < 2
    assert model.i == 0


# ---------- interviewer ----------
def test_good_answer_moves_to_next_planned_question(fake_llm):
    fake_llm([json.dumps(GOOD_EVAL)])
    out = run_step({"session_id": "s", "plan": PLAN, "turns": [answered()]})
    assert out["evaluation"]["overall"] == 4.1
    assert out["next_question"].kind == "main"
    assert out["next_question"].question == PLAN[1].question
    assert out["done"] is False


def test_vague_answer_triggers_follow_up(fake_llm):
    fake_llm([json.dumps(VAGUE_EVAL), json.dumps({"question": "What exactly was your role in the caching work?"})])
    out = run_step({"session_id": "s", "plan": PLAN, "turns": [answered()]})
    nq = out["next_question"]
    assert nq.kind == "followup" and "caching" in nq.question and nq.topic == "APIs"


def test_no_follow_up_on_a_follow_up_or_when_budget_used(fake_llm):
    fake_llm([json.dumps(VAGUE_EVAL)])
    turns = [answered(0, evaluation=GOOD_EVAL | {"overall": 4}), answered(1, kind="followup")]
    out = run_step({"session_id": "s", "plan": PLAN, "turns": turns})
    assert out["next_question"].kind == "main"

    fake_llm([json.dumps(VAGUE_EVAL)])
    out = run_step({"session_id": "s", "plan": PLAN, "turns": [answered()], "max_followups": 0})
    assert out["next_question"].kind == "main"


def test_plan_exhausted_means_done(fake_llm):
    fake_llm([json.dumps(GOOD_EVAL)])
    turns = [answered(0, evaluation=GOOD_EVAL | {"overall": 4}), answered(1, topic="SQL")]
    out = run_step({"session_id": "s", "plan": PLAN, "turns": turns})
    assert out["next_question"] is None and out["done"] is True


# ---------- coach ----------
def test_compute_scores_aggregates():
    t1 = answered(0, evaluation=GOOD_EVAL | {"overall": 4.2})
    t1 = t1.model_copy(update={"nlp": {"wpm": 120, "filler_count": 4, "fillers_per_min": 6, "keyword_coverage": 0.5}})
    t2 = answered(1, evaluation=GOOD_EVAL | {"overall": 3.0, "depth": 2})
    s = compute_scores([t1, t2])
    assert s["overall"] == 3.6
    assert s["criteria"]["depth"] == 3.0
    assert s["speech"]["avg_wpm"] == 120 and s["speech"]["total_fillers"] == 4
    assert s["best"]["index"] == 0 and s["weakest"]["index"] == 1


def test_finish_runs_coach_via_endpoint(fake_llm):
    fake_llm([json.dumps(COACH)])
    turns = [answered(0, evaluation=GOOD_EVAL | {"overall": 4.2}).model_dump()]
    res = client.post("/interview/step", json={"session_id": "s", "plan": [], "turns": turns, "finish": True})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["done"] is True
    assert body["report"]["scores"]["overall"] == 4.2
    assert body["report"]["coach"]["top_improvements"] == ["Quantify results"]
    assert body["report"]["fallback"] is False


def test_coach_fallback(fake_llm):
    fake_llm(["garbage"] * 3)
    turns = [answered(0, evaluation=GOOD_EVAL | {"overall": 4.2}).model_dump()]
    body = client.post("/interview/step", json={"session_id": "s", "turns": turns, "finish": True}).json()
    assert body["report"]["fallback"] is True
    assert body["report"]["coach"]["top_improvements"] == ["State the result with a number"]
