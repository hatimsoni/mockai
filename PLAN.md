# PLAN

Short plan written before each phase. Newest phase at the bottom.

## Service contracts (stable across phases)
```
Browser ──► frontend :3000 ──(fetch, JWT)──► api :4000 ──(HTTP, internal)──► ai :8000
                                               │                              │
                                           Postgres                    Chroma (disk), MinIO (boto3),
                                                                       Ollama :11434, models on disk
```
- API owns users, sessions, answers (Postgres). AI is stateless: API sends the state it needs.
- AI endpoints: `/health`, `/documents/ingest`, `/interview/step`, `/asr/transcribe`,
  `/nlp/analyze`, `/vision/predict`, `/ml/quality`, `/analytics/progress`.

## Phase 0 — setup
- Root files: CLAUDE.md, PLAN.md, PROGRESS.md, .gitignore, docs/DECISIONS.md, docs/MANUAL_STEPS.md.
- `ai/`: FastAPI app with `/health`, settings via pydantic-settings, pytest.
- `api/`: Express + TS with `/health`, Prisma schema stub, vitest + supertest, eslint.
- `frontend/`: create-next-app (TS, Tailwind, App Router), landing page that pings API.
- `infra/docker-compose.yml`: postgres, minio (+ bucket init), ollama, ai, api, frontend.
- Dockerfile per service. `.github/workflows/ci.yml`: lint + test + docker build.
- Tests: pytest (health), vitest (health). Commit "phase 0: ...".
