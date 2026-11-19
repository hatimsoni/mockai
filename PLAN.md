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

## Phase 1 — resume/JD upload + RAG question generation
- ai: `llm.py` (ChatOpenAI → Ollama /v1, override hook for tests, `invoke_json` with Pydantic
  validation + retry), `storage.py` (boto3 → MinIO), `rag/documents.py` (pypdf + recursive
  chunking), `rag/store.py` (Chroma collection per session, MiniLM embeddings),
  `rag/questions.py` (retrieve JD requirements + matching resume chunks → LLM writes a
  question plan citing chunk ids → map ids back to source text).
- ai endpoints: `POST /documents/ingest` (multipart), `POST /questions/plan`.
- api: auth (register/login/me, bcrypt + JWT), repository layer (Prisma impl + in-memory impl
  for tests), AI client, `POST /sessions` (multipart → ingest → plan → first Turn),
  `GET /sessions`, `GET /sessions/:id`. Schema: add `InterviewSession.plan`.
- frontend: auth pages, "new interview" upload form, session page listing planned questions
  with their source chunks.
- tests: pytest (chunking, store retrieval with fake embeddings, invoke_json retry, plan
  endpoint with fake LLM), vitest (auth flow, session creation with fake AI).

## Phase 2 — interview UI + audio recording + ASR
- ai: `asr.py` — faster-whisper `small` int8 on CPU (lazy singleton, override hook for tests),
  VAD filter, word timestamps, `initial_prompt` that (a) biases vocabulary toward JD terms and
  (b) nudges Whisper to keep fillers ("um", "uh") which it normally deletes. Endpoint
  `POST /asr/transcribe` (multipart) also stores audio in MinIO.
- api: `POST /sessions/:id/answer` (multipart audio + durationSec) answers the current turn:
  transcribe → save → create next turn from the plan (phase 3 swaps in the agent graph).
  `POST /sessions/:id/finish`.
- frontend: `useRecorder` hook (getUserMedia + MediaRecorder, webm/opus), question read aloud
  with the browser's free speechSynthesis, timer, upload, transcript display, progress.
- tests: pytest for transcript/word mapping with a fake Whisper; vitest for answer flow.
