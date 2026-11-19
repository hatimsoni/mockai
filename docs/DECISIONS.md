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
