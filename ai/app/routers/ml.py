"""Phase 6 endpoint: classic ML answer-quality baseline."""
from fastapi import APIRouter
from pydantic import BaseModel

from app import quality

router = APIRouter(tags=["ml"])


class QualityRequest(BaseModel):
    question: str
    answer: str


class QualityResponse(BaseModel):
    available: bool
    score: float | None = None
    label: int | None = None
    probabilities: dict[str, float] | None = None


@router.post("/ml/quality", response_model=QualityResponse)
def predict_quality(req: QualityRequest) -> QualityResponse:
    result = quality.predict(req.question, req.answer)
    return QualityResponse(available=result is not None, **(result or {}))
