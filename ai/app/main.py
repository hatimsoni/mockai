"""FastAPI entry point for the AI service.

Run: uvicorn app.main:app --reload --port 8000
Docs: http://localhost:8000/docs (auto-generated OpenAPI UI)
"""
import logging

from fastapi import Depends, FastAPI, Header, HTTPException

from app.config import get_settings
from app.routers import analytics, documents, interview, ml, speech, vision

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
for noisy in ("httpx", "httpcore", "chromadb", "sentence_transformers"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

app = FastAPI(title="AI Mock Interview Coach — AI service", version="0.1.0")


def require_internal_key(x_internal_key: str | None = Header(default=None)) -> None:
    """Only the API gateway may call us. Disabled when INTERNAL_API_KEY is empty."""
    expected = get_settings().internal_api_key
    if expected and x_internal_key != expected:
        raise HTTPException(status_code=401, detail="invalid internal key")


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "service": "ai", "llm_model": s.llm_model}


protected = [Depends(require_internal_key)]
app.include_router(documents.router, dependencies=protected)
app.include_router(speech.router, dependencies=protected)
app.include_router(interview.router, dependencies=protected)
app.include_router(vision.router, dependencies=protected)
app.include_router(ml.router, dependencies=protected)
app.include_router(analytics.router, dependencies=protected)
