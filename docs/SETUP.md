# Setup guide

Two ways to run: **Docker (one command)** or **dev mode** (each service on your machine, hot reload).

## Requirements
- 16 GB RAM laptop, no GPU needed. ~15 GB free disk (images + models).
- Docker Desktop (Windows: WSL2 backend) with ≥ 8 GB RAM assigned.
- For dev mode: Node.js 20+, Python 3.11/3.12, Ollama (https://ollama.com/download).

## A. Docker (recommended)
```bash
cp infra/.env.example infra/.env        # set JWT_SECRET and INTERNAL_API_KEY to long random strings
docker compose -f infra/docker-compose.yml up -d --build
docker compose -f infra/docker-compose.yml exec ollama ollama pull qwen2.5:7b-instruct   # ~4.7 GB, once
```
Open http://localhost:3000 (API migrations run automatically on start).
MinIO console: http://localhost:9001. AI service docs: http://localhost:8000/docs.

## B. Dev mode
```bash
# infra only
docker compose -f infra/docker-compose.yml up -d postgres minio minio-init
ollama pull qwen2.5:7b-instruct

# ai (terminal 1)
cd ai
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt   # macOS/Linux: .venv/bin/
cp .env.example .env
.venv/Scripts/uvicorn app.main:app --reload --port 8000

# api (terminal 2)
cd api && npm install && cp .env.example .env
npx prisma migrate deploy && npm run dev

# frontend (terminal 3)
cd frontend && npm install && npm run dev
```
First answer triggers the Whisper `small` download (~480 MB); first upload triggers MiniLM (~90 MB).

## Tests
```bash
cd ai && .venv/Scripts/python -m pytest -q && .venv/Scripts/python -m pytest -q ../ml/tests
cd api && npm test && npm run lint && npm run typecheck
cd frontend && npm test && npm run lint && npm run build
```
All tests run offline: LLM, Whisper and embeddings are replaced by fakes.

## Low on RAM?
- `LLM_MODEL=qwen2.5:3b-instruct` (≈2 GB) — lower quality questions/feedback, much faster.
- Or point `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` at a free OpenAI-compatible host.
- `WHISPER_MODEL=base` halves ASR memory and time.

## Troubleshooting
| Symptom | Fix |
|---|---|
| "AI service unreachable" | is uvicorn / the `ai` container up? `curl localhost:8000/health` |
| Questions are generic ("The role mentions…") | the LLM was unreachable → fallback questions. Check Ollama: `curl localhost:11434/api/tags` |
| "approximate score" badge | the Evaluator LLM failed; the baseline model scored it instead |
| Camera says permission denied | allow camera in the address bar; the interview works without it |
| Mic recording empty | allow microphone; use Chrome/Edge/Firefox over `localhost` (or HTTPS) |
