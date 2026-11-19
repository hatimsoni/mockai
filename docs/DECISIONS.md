# Decisions

One line each: what, and why.

## Phase 0 — setup
- **npm (not pnpm/yarn), separate `package.json` per service** — fewest tools to install; each service builds its own Docker image.
- **Ollama accessed through its OpenAI-compatible `/v1` endpoint** — one client (`langchain-openai`) works for local Ollama *and* any free hosted OpenAI-compatible API; switching is just `LLM_BASE_URL`.
- **AI service is stateless** — interview state lives in Postgres (owned by the API) and is sent with each request, so the AI pods can scale horizontally in Kubernetes.
- **AI service owns object storage (boto3)** — the spec asks for boto3; the AI service is also the one that reads PDFs/audio, so it stores them and returns the object key; the API keeps only keys.
- **Express + Prisma + Zod in the API** — familiar MERN-ish stack, Prisma gives typed queries and migrations, Zod validates request bodies.
- **Vitest for the API, pytest for AI** — both fast, zero-config.
- **Heavy imports (torch, whisper, sentence-transformers) are lazy** — the FastAPI app starts and unit tests run without downloading any model.
- **Docker and Ollama were not installed on the build machine** — compose/K8s files are written and linted but must be run manually (see MANUAL_STEPS.md).
- **Prisma 6 (not 7)** — Prisma 7 requires driver adapters + `prisma.config.ts`; v6 is simpler to learn and fully supported.
- **`.gitattributes` forces LF** — Dockerfiles and shell scripts run in Linux containers; CRLF breaks them.

## Phase 1 — RAG
- **Question plan generated once up front** — one LLM call (≈30–60 s on CPU) instead of one per question; the Interviewer agent (phase 3) adds follow-ups on top.
- **Per-requirement retrieval (each JD chunk → 2 nearest resume chunks)** — better coverage than a single query with the whole JD, which is dominated by its longest topic.
- **One Chroma collection per session** — simple isolation and cleanup; fine at portfolio scale.
- **Chunk size 500 / overlap 80 chars** — roughly one resume bullet group; MiniLM truncates at 256 tokens anyway.
- **Deterministic fallback questions** — if the LLM is down or keeps returning invalid JSON the user still gets an interview.
- **Repository interface + in-memory implementation in the API** — route tests run without Postgres.
- **JWT in localStorage** — simplest for an SPA-style demo; production would use httpOnly cookies to reduce XSS token theft (noted as a known trade-off).
- **Session creation is synchronous (~1 min)** — simpler than a job queue; a queue (BullMQ/Redis) is the upgrade path.
