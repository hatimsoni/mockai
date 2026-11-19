"""Builds a tiny real PDF in memory so we test the true parsing path."""
from __future__ import annotations


def make_pdf(text: str) -> bytes:
    """Minimal single-page PDF with Helvetica text, one line per '\\n'."""
    lines = text.split("\n")
    ops = ["BT", "/F1 11 Tf", "14 TL", "50 780 Td"]
    for line in lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        ops.append(f"({safe}) Tj T*")
    ops.append("ET")
    stream = "\n".join(ops).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return bytes(out)


RESUME = """Jane Doe - Full Stack Developer
Experience: Built REST APIs with Node.js and Express serving 50k users.
Migrated a React frontend to Next.js, cutting page load time by 40 percent.
Designed PostgreSQL schemas and wrote Prisma migrations.
Projects: Chat app with WebSockets and Redis pub/sub.
Skills: TypeScript, React, Node.js, PostgreSQL, Docker, AWS."""

JD = """We are hiring a Backend Engineer.
Responsibilities: design and build scalable REST APIs in Node.js.
Requirements: strong PostgreSQL skills, Docker and Kubernetes experience.
Nice to have: experience with message queues and caching (Redis)."""
