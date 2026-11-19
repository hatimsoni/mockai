"""Turn a resume PDF and a job description into small, embeddable chunks.

Concept — chunking: an embedding squeezes a text into one vector. A whole resume in one
vector is too blurry to match a specific JD requirement, so we split it into ~500
character pieces. `RecursiveCharacterTextSplitter` tries to split on paragraphs first,
then lines, then sentences, then words, so chunks stay semantically whole.
The overlap (~80 chars) keeps a sentence that straddles a boundary present in both chunks.
"""
from __future__ import annotations

import io
import re

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings


def extract_pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return clean_text("\n\n".join(pages))


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)  # collapse runs of spaces
    text = re.sub(r"\n{3,}", "\n\n", text)  # at most one blank line
    return text.strip()


def chunk_text(text: str, source: str) -> list[Document]:
    """Split text into Documents tagged with their source ("resume" or "jd")."""
    s = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=s.chunk_size,
        chunk_overlap=s.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    pieces = splitter.split_text(clean_text(text))
    return [
        Document(page_content=p, metadata={"source": source, "chunk": i}) for i, p in enumerate(pieces)
    ]
