# PROGRESS

## Done
- **Phase 0 — setup**: monorepo; FastAPI/Express/Next.js hello-worlds; Prisma schema + init
  migration; Dockerfiles; `infra/docker-compose.yml`; GitHub Actions CI.
- **Phase 1 — upload + RAG**: pypdf → chunking → MiniLM embeddings → Chroma (per session);
  question plan with citations via `invoke_json` (Pydantic + retry + fallback); API auth (JWT,
  bcrypt), repository layer, `POST/GET /sessions`; frontend auth pages, new-interview form,
  interview page with "why this question?" sources.
  Tests: ai 12 pytest, api 9 vitest. Real MiniLM + Chroma smoke-tested locally.

## Pending
- Phases 2–9.

## Known issues
- Docker, Ollama, kind not installed on build machine: compose/images not run locally
  (see `docs/MANUAL_STEPS.md`). LLM paths tested with a fake chat model only.
- Session creation is synchronous (~1 min on CPU with a 7B model).

## Next step
Phase 2: interview UI with mic recording (MediaRecorder) → API upload → AI `/asr/transcribe`
(faster-whisper, word timestamps) → store transcript on the Turn.
