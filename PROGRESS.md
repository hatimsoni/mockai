# PROGRESS

## Done
- **Phase 0 — setup**: monorepo; FastAPI `/health` (pytest), Express `/health` (vitest + supertest),
  Next.js 16 app with `/api/*` proxy to Express; full Prisma schema + `0001_init` migration;
  Dockerfiles for all 3 services; `infra/docker-compose.yml` (Postgres, MinIO + bucket init,
  Ollama, ai, api, frontend); GitHub Actions CI (lint + test + docker build).

## Pending
- Phases 1–9.

## Known issues
- Docker, Ollama, kind not installed on build machine: compose and images not run locally yet
  (see `docs/MANUAL_STEPS.md`). CI builds the images on GitHub.

## Next step
Phase 1: resume/JD upload + RAG question generation (`ai/app/rag/`, `api/src/routes/sessions.ts`).
