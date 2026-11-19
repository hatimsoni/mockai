# Manual steps

Things the build could not do automatically (need installs, accounts, a webcam, a GPU,
or a human). Each step is exact. Do them in order the first time.

## 1. Install the free tools (one time)
1. **Docker Desktop** — https://www.docker.com/products/docker-desktop/ (enable WSL2 backend on Windows).
   Give it at least **8 GB RAM** in Settings → Resources (Ollama + 7B model needs ~5 GB).
2. **Node.js 20+** and **Python 3.11/3.12**.
3. Optional (for running Ollama outside Docker, faster on Windows): https://ollama.com/download

## 2. First run with Docker
```bash
cp infra/.env.example infra/.env          # edit JWT_SECRET to any long random string
docker compose -f infra/docker-compose.yml up -d --build
# pull the LLM into the Ollama container (≈4.7 GB download, one time)
docker compose -f infra/docker-compose.yml exec ollama ollama pull qwen2.5:7b-instruct
# create DB tables
docker compose -f infra/docker-compose.yml exec api npx prisma migrate deploy
```
Open http://localhost:3000. MinIO console: http://localhost:9001 (minioadmin / minioadmin).

> Low on RAM? Set `LLM_MODEL=qwen2.5:3b-instruct` in `infra/.env` and pull that instead (≈2 GB).
