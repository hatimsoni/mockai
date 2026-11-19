"""Vector store: embeddings + ChromaDB.

Concept — embeddings: a model (all-MiniLM-L6-v2, 22M params, runs fine on CPU) maps text
to a 384-number vector so that texts with similar *meaning* land close together.
"Built REST APIs in Express" and "backend web services with Node" score as similar even
with no shared keywords. Chroma stores the vectors on disk and finds the nearest ones
to a query vector (cosine distance) — that's the "retrieval" in RAG.

One Chroma collection per interview session keeps each user's documents isolated.
"""
from __future__ import annotations

import re
from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.config import get_settings

_embeddings_override: Embeddings | None = None


def set_embeddings_override(emb: Embeddings | None) -> None:
    """Tests inject a tiny fake embedding model so no download is needed."""
    global _embeddings_override
    _embeddings_override = emb


@lru_cache
def _hf_embeddings() -> Embeddings:
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=get_settings().embedding_model,
        model_kwargs={"device": "cpu"},
        # unit-length vectors -> dot product == cosine similarity
        encode_kwargs={"normalize_embeddings": True},
    )


def get_embeddings() -> Embeddings:
    return _embeddings_override or _hf_embeddings()


@lru_cache
def _chroma_client(path: str):
    import chromadb

    return chromadb.PersistentClient(path=path)


def collection_name(session_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "-", session_id)[:60]
    return f"session-{safe}"


def _store(session_id: str):
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=collection_name(session_id),
        embedding_function=get_embeddings(),
        client=_chroma_client(get_settings().chroma_dir),
        collection_metadata={"hnsw:space": "cosine"},
    )


def index_documents(session_id: str, docs: list[Document]) -> int:
    """(Re)build the session's collection from scratch. Returns number of chunks stored."""
    store = _store(session_id)
    store.delete_collection()  # idempotent re-ingest
    store = _store(session_id)
    if docs:
        ids = [f"{d.metadata['source']}-{d.metadata['chunk']}" for d in docs]
        store.add_documents(docs, ids=ids)
    return len(docs)


def retrieve(session_id: str, query: str, k: int = 4, source: str | None = None) -> list[Document]:
    """Top-k chunks most similar to `query`, optionally only from one source."""
    store = _store(session_id)
    where = {"source": source} if source else None
    return store.similarity_search(query, k=k, filter=where)


def all_chunks(session_id: str, source: str) -> list[Document]:
    data = _store(session_id).get(where={"source": source})
    docs = [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(data["documents"], data["metadatas"], strict=False)
    ]
    return sorted(docs, key=lambda d: d.metadata.get("chunk", 0))
