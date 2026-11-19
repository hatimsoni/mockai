import json

from fastapi.testclient import TestClient

from app.main import app
from app.rag.documents import chunk_text, extract_pdf_text
from app.rag.store import index_documents, retrieve
from tests.helpers import JD, RESUME, make_pdf

client = TestClient(app)


def test_pdf_text_extraction():
    text = extract_pdf_text(make_pdf(RESUME))
    assert "Node.js and Express" in text


def test_chunking_tags_source_and_respects_size(monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "120")
    monkeypatch.setenv("CHUNK_OVERLAP", "20")
    from app.config import get_settings

    get_settings.cache_clear()
    docs = chunk_text(RESUME, "resume")
    assert len(docs) > 1
    assert all(d.metadata["source"] == "resume" for d in docs)
    assert all(len(d.page_content) <= 120 for d in docs)
    assert [d.metadata["chunk"] for d in docs] == list(range(len(docs)))


def test_retrieve_filters_by_source():
    docs = chunk_text(RESUME, "resume") + chunk_text(JD, "jd")
    index_documents("s1", docs)
    hits = retrieve("s1", "PostgreSQL", k=3, source="jd")
    assert hits and all(h.metadata["source"] == "jd" for h in hits)


def test_reingest_replaces_old_chunks():
    index_documents("s2", chunk_text("old content about cobol " * 5, "resume"))
    index_documents("s2", chunk_text(RESUME, "resume"))
    hits = retrieve("s2", "anything", k=50)
    assert not any("cobol" in h.page_content for h in hits)


def test_ingest_endpoint():
    res = client.post(
        "/documents/ingest",
        data={"session_id": "abc", "jd_text": JD},
        files={"resume": ("cv.pdf", make_pdf(RESUME), "application/pdf")},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["chunks"]["resume"] >= 1 and body["chunks"]["jd"] >= 1
    assert body["resume_key"] is None  # storage disabled in tests


def test_ingest_rejects_non_pdf():
    res = client.post(
        "/documents/ingest",
        data={"session_id": "abc", "jd_text": JD},
        files={"resume": ("cv.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 400


def test_plan_maps_source_ids_and_drops_hallucinated(fake_llm):
    index_documents("p1", chunk_text(RESUME, "resume") + chunk_text(JD, "jd"))
    fake_llm(
        [
            json.dumps(
                {
                    "questions": [
                        {
                            "question": "How did you design the REST APIs serving 50k users?",
                            "topic": "REST APIs",
                            "type": "resume",
                            "source_ids": ["R1", "J1", "Z9"],
                        }
                    ]
                }
            )
        ]
    )
    res = client.post("/questions/plan", json={"session_id": "p1", "num_questions": 1})
    assert res.status_code == 200, res.text
    q = res.json()["questions"][0]
    assert q["topic"] == "REST APIs"
    assert {s["id"] for s in q["sources"]} == {"R1", "J1"}  # Z9 does not exist -> dropped


def test_plan_falls_back_when_llm_returns_garbage(fake_llm):
    index_documents("p2", chunk_text(RESUME, "resume") + chunk_text(JD, "jd"))
    fake_llm(["not json", "still not json", "nope"])
    res = client.post("/questions/plan", json={"session_id": "p2", "num_questions": 2})
    assert res.status_code == 200
    qs = res.json()["questions"]
    assert len(qs) == 2 and qs[0]["sources"][0]["source"] == "jd"
