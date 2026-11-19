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

## 3. Record webcam data and train the attention model (optional, ~30 min)
Until you do this, attention uses a rule-based heuristic (works for obvious head turns / looking down).
1. Start the app, open http://localhost:3000/vision-lab, click **Start camera**.
2. Hold **A** while looking at the screen (talk, gesture, move a bit); hold **L** while looking away
   (phone, notes, other monitor, window, ceiling). Aim for at least 500 frames of each.
3. **Download CSV** into `ml/vision/data/`. Repeat on 3+ different sessions (lighting, glasses, distance).
4. Train and install: `ai/.venv/Scripts/python ml/vision/train_attention.py`
5. Restart the AI service (`docker compose restart ai`, or re-run uvicorn). `/vision/predict` now returns `"model": "mlp"`.
Details and the reasoning behind the amounts: `ml/vision/README.md`.

## 4. Build the real (human-labelled) answer dataset (optional, ~2–3 h, mostly waiting)
The committed models are trained on a template-generated seed set (synthetic). For honest results:
1. Make sure Ollama runs locally with the model pulled (`ollama pull qwen2.5:7b-instruct`).
2. Generate answers (resumable; ~1–1.5 h on CPU for 160 answers):
   `ai/.venv/Scripts/python ml/dataset/generate_llm.py --per-score 2`
3. Label them yourself (ENTER accepts the LLM's intended score; stop/resume any time):
   `ai/.venv/Scripts/python ml/dataset/label.py`
4. Re-split and retrain everything, then rebuild the table:
   ```bash
   ai/.venv/Scripts/python ml/dataset/split.py
   ai/.venv/Scripts/python ml/classic/train_sklearn.py
   ai/.venv/Scripts/python ml/classic/train_keras.py      # needs: pip install -r ml/requirements.txt
   ai/.venv/Scripts/python ml/results/compare.py
   ```
5. Restart the AI service so it loads the new `ai/models/quality_baseline.joblib`.
