"""Phase 5 endpoint: landmark frames in, attention probabilities out."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.vision.features import RAW_DIM
from app.vision.model import get_predictor

router = APIRouter(tags=["vision"])


class VisionRequest(BaseModel):
    # each frame: 15 landmarks x (x, y, z) = 45 numbers; max 40 frames (20 s) per call
    frames: list[list[float]] = Field(min_length=1, max_length=40)


class VisionResponse(BaseModel):
    probabilities: list[float]
    attentive: list[bool]
    model: str  # "mlp" (trained) or "heuristic"


@router.post("/vision/predict", response_model=VisionResponse)
def predict(req: VisionRequest) -> VisionResponse:
    if any(len(f) != RAW_DIM for f in req.frames):
        raise HTTPException(422, f"each frame must have {RAW_DIM} numbers")
    predictor = get_predictor()
    probs = predictor.predict_proba(req.frames)
    return VisionResponse(
        probabilities=[round(float(p), 3) for p in probs],
        attentive=[bool(p >= 0.5) for p in probs],
        model=predictor.kind,
    )
