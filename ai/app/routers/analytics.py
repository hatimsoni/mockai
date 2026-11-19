"""Phase 8 endpoint: Pandas aggregation of a user's interview history."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.analytics import SessionData, progress

router = APIRouter(tags=["analytics"])


class ProgressRequest(BaseModel):
    sessions: list[SessionData] = Field(default_factory=list, max_length=500)


@router.post("/analytics/progress")
def analytics_progress(req: ProgressRequest) -> dict:
    return progress(req.sessions)
