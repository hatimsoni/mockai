"""Phase 1 endpoints: ingest documents, plan questions."""
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app import storage
from app.rag.documents import chunk_text, extract_pdf_text
from app.rag.questions import Question, plan_questions
from app.rag.store import index_documents

router = APIRouter(tags=["rag"])

MAX_PDF_BYTES = 5 * 1024 * 1024


class IngestResult(BaseModel):
    session_id: str
    resume_key: str | None
    resume_chars: int
    chunks: dict[str, int]


@router.post("/documents/ingest", response_model=IngestResult)
def ingest(
    session_id: str = Form(...),
    jd_text: str = Form(...),
    resume: UploadFile = File(...),
) -> IngestResult:
    # sync def: FastAPI runs it in a worker thread, so CPU-heavy embedding
    # does not block the event loop for other requests.
    data = resume.file.read()
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, "resume larger than 5 MB")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "resume must be a PDF")
    try:
        resume_text = extract_pdf_text(data)
    except Exception as err:  # noqa: BLE001
        raise HTTPException(400, f"could not read PDF: {err}") from err
    if len(resume_text) < 50:
        raise HTTPException(400, "no text found in PDF (scanned image? export it as a text PDF)")

    key = storage.upload_bytes(f"resumes/{session_id}.pdf", data, "application/pdf")
    resume_docs = chunk_text(resume_text, "resume")
    jd_docs = chunk_text(jd_text, "jd")
    index_documents(session_id, resume_docs + jd_docs)
    return IngestResult(
        session_id=session_id,
        resume_key=key,
        resume_chars=len(resume_text),
        chunks={"resume": len(resume_docs), "jd": len(jd_docs)},
    )


class PlanRequest(BaseModel):
    session_id: str
    job_title: str = "Software Engineer"
    num_questions: int = Field(default=5, ge=1, le=15)


class PlanResponse(BaseModel):
    questions: list[Question]


@router.post("/questions/plan", response_model=PlanResponse)
def plan(req: PlanRequest) -> PlanResponse:
    return PlanResponse(questions=plan_questions(req.session_id, req.job_title, req.num_questions))
