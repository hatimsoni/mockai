"""Phase 3 endpoint: run one step of the agent graph."""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.graph import run_step
from app.agents.state import NextQuestion, PlanItem, TurnIn

router = APIRouter(tags=["agents"])


class StepRequest(BaseModel):
    session_id: str
    job_title: str = "Software Engineer"
    plan: list[PlanItem] = Field(default_factory=list)
    turns: list[TurnIn] = Field(default_factory=list)
    finish: bool = False
    max_followups: int = Field(default=2, ge=0, le=5)


class StepResponse(BaseModel):
    evaluation: dict[str, Any] | None = None  # evaluation of the latest answer (if one was scored)
    next_question: NextQuestion | None = None
    done: bool = False
    report: dict[str, Any] | None = None


@router.post("/interview/step", response_model=StepResponse)
def step(req: StepRequest) -> StepResponse:
    out = run_step(
        {
            "session_id": req.session_id,
            "job_title": req.job_title,
            "plan": req.plan,
            "turns": req.turns,
            "finish": req.finish,
            "max_followups": req.max_followups,
        }
    )
    return StepResponse(
        evaluation=out.get("evaluation"),
        next_question=out.get("next_question"),
        done=bool(out.get("done")),
        report=out.get("report"),
    )
