"""Phase 6 endpoint: classic ML answer-quality baseline."""
from fastapi import APIRouter
from pydantic import BaseModel

from app import finetuned, quality

router = APIRouter(tags=["ml"])


class QualityRequest(BaseModel):
    question: str
    answer: str


class QualityResponse(BaseModel):
    available: bool
    score: float | None = None
    label: int | None = None
    probabilities: dict[str, float] | None = None
    finetuned_score: int | None = None  # LoRA model via Ollama, if SCORER_MODEL is set


@router.post("/ml/quality", response_model=QualityResponse)
def predict_quality(req: QualityRequest) -> QualityResponse:
    result = quality.predict(req.question, req.answer)
    return QualityResponse(
        available=result is not None,
        finetuned_score=finetuned.score(req.question, req.answer),
        **(result or {}),
    )
