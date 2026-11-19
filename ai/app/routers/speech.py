"""Speech endpoints: audio -> transcript (phase 2), transcript -> speech metrics (phase 4)."""
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app import asr, storage
from app.nlp import NlpMetrics, analyze, extract_keywords

router = APIRouter(tags=["speech"])

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # ~25 min of opus audio; answers are 1-3 min


class TranscribeResponse(asr.Transcript):
    audio_key: str | None


@router.post("/asr/transcribe", response_model=TranscribeResponse)
def transcribe(
    audio: UploadFile = File(...),
    session_id: str = Form("adhoc"),
    turn_index: int = Form(0),
    keywords: str = Form("[]"),  # JSON list of terms to bias the decoder
    jd_text: str = Form(""),  # or: extract the terms from the job description
) -> TranscribeResponse:
    data = audio.file.read()
    if not data:
        raise HTTPException(400, "empty audio")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "audio too large")
    try:
        terms = [str(k) for k in json.loads(keywords)]
    except (ValueError, TypeError):
        terms = []
    if not terms and jd_text:
        terms = extract_keywords(jd_text)

    ext = ".webm"
    if audio.filename and "." in audio.filename:
        ext = "." + audio.filename.rsplit(".", 1)[1].lower()[:5]
    key = storage.upload_bytes(f"audio/{session_id}/{turn_index}{ext}", data, audio.content_type or "audio/webm")
    try:
        result = asr.transcribe(data, keywords=terms, suffix=ext)
    except Exception as err:  # noqa: BLE001 - corrupt/unsupported audio
        raise HTTPException(400, f"could not decode audio: {err}") from err
    return TranscribeResponse(**result.model_dump(), audio_key=key)


class AnalyzeRequest(BaseModel):
    transcript: str
    jd_text: str = ""
    words: list[dict] | None = None  # Whisper word timestamps
    duration_sec: float | None = None


@router.post("/nlp/analyze", response_model=NlpMetrics)
def nlp_analyze(req: AnalyzeRequest) -> NlpMetrics:
    return analyze(req.transcript, jd_text=req.jd_text, words=req.words, duration_sec=req.duration_sec)
