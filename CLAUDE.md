# CLAUDE.md — AI Mock Interview Coach

Guidance for any AI assistant (or human) continuing work on this repo.
Read `PROGRESS.md` first: it says what's done and the exact next step.

## Product
User uploads resume (PDF) + job description. App runs a **spoken** mock interview:
questions grounded in resume + JD (RAG), records spoken answers (ASR), watches webcam
attention (face landmarks only, never video), scores each answer (agents), writes a
feedback report, and shows progress across sessions on a dashboard.

## Hard constraint: 100% free, runs on a 16 GB CPU-only laptop
| Concern | Choice |
|---|---|
| LLM | Ollama local, default `qwen2.5:7b-instruct` (`LLM_MODEL`). Optional free-tier OpenAI-compatible host via `LLM_BASE_URL` / `LLM_API_KEY`. Local must always work. |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (local) |
| Vector DB | ChromaDB, persistent on disk |
| ASR | faster-whisper `small`, CPU, int8 |
| Object storage | MinIO (Docker) via boto3 S3 API — AWS S3 is a config change |
| DB | PostgreSQL (Docker) via Prisma |
| GPU work | Only fine-tuning, in a free Google Colab T4 notebook |

## Monorepo
```
frontend/  Next.js App Router + TS + Tailwind (interview UI, webcam, mic, report, dashboard)
api/       Express + TS gateway: JWT auth, sessions, uploads, Prisma/Postgres, calls /ai
ai/        FastAPI: RAG, LangGraph agents, ASR, NLP, vision inference, scoring, analytics
ml/        Training: dataset builder, sklearn + Keras baselines, vision MLP, LoRA notebook
infra/     docker-compose, Kubernetes manifests (kind/minikube), CI lives in .github/
docs/      architecture, setup, DECISIONS, MANUAL_STEPS, deployment, learn/phase-N.md
```

## AI features → skill shown
1. RAG (LangChain + Chroma) — personalised questions with source refs
2. Agents (LangGraph) — Interviewer / Evaluator (strict Pydantic JSON + retries) / Coach
3. ASR — faster-whisper with word timestamps
4. NLP (NLTK) — fillers, WPM, JD keyword coverage, sentence stats
5. Vision (PyTorch MLP on MediaPipe landmarks) — attentive vs looking away
6. Classic ML — TF-IDF + LogisticRegression vs Keras, metrics table
7. Fine-tuning — LoRA on Qwen2.5-0.5B-Instruct in Colab, compared vs base + sklearn
8. Dashboard — Pandas aggregation → charts

## Working rules
- Phases 0–9 in order. Before a phase: short plan in `PLAN.md`. After a phase:
  run all tests and fix failures → commit `phase N: <summary>` → update `PROGRESS.md`.
- Decisions go in `docs/DECISIONS.md` (one line reason each).
- Anything needing money, accounts, keys, manual actions (Colab, webcam recording) or
  irreversible steps: prepare everything, write steps in `docs/MANUAL_STEPS.md`, move on.
- Simple, readable code > clever. Comment AI concepts inline.
- Tests: pytest in `ai/`, vitest in `api/`. Heavy models (whisper, torch weights,
  embeddings, LLM) must be mockable so tests run offline and fast.
- Never commit secrets. Only `.env.example` files.
- If something won't run on CPU/16 GB, pick a lighter alternative and log it.
- When fixing bugs: find + explain root cause first; don't touch unrelated code.
- Every phase gets `docs/learn/phase-N.md`: what/how, concepts from zero, key files,
  5 interview Q&As, 2 exercises.

## Commands
```bash
# everything
docker compose -f infra/docker-compose.yml up --build
# ai
cd ai && python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
cd ai && .venv/Scripts/python -m pytest -q
cd ai && .venv/Scripts/uvicorn app.main:app --reload --port 8000
# api
cd api && npm install && npx prisma generate && npm test && npm run dev
# frontend
cd frontend && npm install && npm run dev
```
