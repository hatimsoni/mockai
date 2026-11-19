con# PLAN

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

## Phase 3 — LangGraph agents (Interviewer, Evaluator, Coach) + report page
- ai `app/agents/`: shared `InterviewState`; **Evaluator** scores the latest answer (relevance,
  depth, clarity, STAR 1-5 + STAR breakdown, strengths, improvements, needs_follow_up) as strict
  Pydantic JSON with retries, heuristic fallback; overall = weighted mean computed in code.
  **Interviewer** decides: follow-up (LLM writes it, grounded in retrieved resume chunks) or next
  planned question, max 2 follow-ups per interview, one per topic. **Coach** writes the final
  report from all evaluations; numeric aggregates computed in code.
- Graph: START → (unevaluated answer? evaluator) → (finish? coach : interviewer) → END.
  Endpoint `POST /interview/step` (stateless: API sends plan + turns).
- api: answer route calls `ai.step` → saves evaluation/score, creates follow-up or next turn;
  finish route calls `ai.step(finish)` → saves report + overallScore.
- frontend: report page (overall score, category bars, per-question feedback, coach advice).
- tests: graph routing, evaluator retry/fallback, follow-up limits, coach aggregation (fake LLM);
  vitest for follow-up turn creation + report saving.

## Phase 4 — NLP speech analysis (NLTK)
- ai `app/nlp.py`: tokenize (punkt), filler detection (single + multi-word, context rule for
  "like"/"so"), WPM from word timestamps (speaking span, not recording length), long pauses
  (> 2 s gaps), JD keyword extraction (POS-tag nouns + tech tokens, stopwords removed, ranked by
  frequency) and coverage with Porter stemming, sentence-length stats, lexical diversity.
- `POST /nlp/analyze`; `/asr/transcribe` accepts `jd_text` and biases Whisper with JD keywords.
- api: answer route calls analyze after ASR, stores `turn.nlp` before the agents run (the
  Evaluator sees the metrics).
- frontend already renders `NlpMetrics`; tune keyword-coverage threshold.
- tests: pytest for each metric on hand-made transcripts.

## Phase 5 — vision: landmarks → PyTorch attention classifier
- Contract: 15 MediaPipe FaceMesh key points (nose, chin, forehead, eye corners/lids, irises,
  cheeks) × (x, y, z) = 45 numbers per frame, captured in the browser every 500 ms. Same index
  list in `ai/app/vision/features.py` and `frontend/src/lib/landmarks.ts` (a test parses the TS
  file to prevent train/serve skew).
- ai `app/vision/`: features (normalize by nose + inter-ocular distance; add yaw/pitch/iris-ratio
  features → 51), `AttentionMLP` (51→32→16→1), predictor that loads `models/attention_mlp.pt`
  with saved standardization stats, heuristic fallback until trained. `POST /vision/predict`.
- ml `ml/vision/`: `record_landmarks.py` (OpenCV + MediaPipe, keys label frames), browser
  `/vision-lab` page (same extractor as production) exporting CSV, `train_attention.py`
  (group split by recording, early stopping, metrics JSON), `synthetic.py` for tests only.
  Data guide in `ml/vision/README.md`.
- api: `POST /sessions/:id/attention` proxy (zod-validated frames); answer route stores the
  attention summary sent with the audio.
- frontend: `useFaceLandmarks` hook (@mediapipe/tasks-vision), webcam panel with live
  attention, per-answer summary (`lib/attention.ts`, unit-tested with vitest).

## Phase 6 — classic ML baselines (scikit-learn + Keras) + dataset builder
- Dataset schema (`ml/data/*.csv`): id, question, answer, label (1-5), source, intended_score.
- `ml/dataset/build_seed.py`: template generator (no LLM) — answers composed from rubric
  components (relevance, specifics/metrics, STAR parts, vagueness/fillers) → rubric label + noise.
  Lets everything run offline/CI; honestly flagged as synthetic.
- `ml/dataset/generate_llm.py`: local LLM writes answers targeting each score 1-5 per question
  (intended_score); `ml/dataset/label.py`: CLI for manual labels; `ml/dataset/split.py`: merge +
  stratified train/val/test with fixed seed (the same test set is reused by phase 7).
- `ml/classic/train_sklearn.py`: majority + length-only baselines, TF-IDF(1-2 grams) +
  LogisticRegression with GridSearchCV; metrics: accuracy, macro-F1, MAE, QWK, within-1; exports
  `ai/models/quality_baseline.joblib`. `ml/classic/train_keras.py`: TextVectorization → Embedding →
  pooling → Dense softmax, early stopping. `ml/results/compare.py` → `RESULTS.md` table.
- ai: `/ml/quality` serves the sklearn pipeline (expected score from class probabilities);
  evaluator heuristic fallback uses it when the LLM is down. API stores `turn.baselineScore`.
- tests: pytest for seed generator determinism, metrics helpers, `/ml/quality` with a tiny model.

## Phase 7 — LoRA fine-tuning (Colab T4) + evaluation comparison
- Shared scoring prompt in `ai/app/scoring_prompt.py`; the notebook embeds the same text (a test
  checks the notebook contains it → no prompt skew between training and serving).
- `ml/finetune/lora_qwen_scoring.ipynb`: load `ml/data/{train,val,test}.csv` (git clone or
  upload), Qwen2.5-0.5B-Instruct fp16, score = argmax/expected value over the logits of tokens
  "1".."5" (no free-text parsing), zero-shot base eval → LoRA (r=16, all linear proj, completion-only
  loss, 3 epochs, ~5-10 min on T4) → eval on the same test set → table vs sklearn/Keras →
  `lora_metrics.json`; export adapter, merged model, GGUF (llama.cpp) + Ollama `Modelfile`.
  `SMOKE_TEST` mode (auto when no GPU) runs a tiny subset on CPU — used to verify the notebook locally.
- `ml/finetune/build_notebook.py` generates the .ipynb from readable Python cell sources.
- ai: optional `SCORER_MODEL` (e.g. Ollama `mockai-scorer`) → `/ml/quality` also returns
  `finetuned_score` using the shared prompt.
- MANUAL_STEPS: run in Colab, copy `lora_metrics.json`, `ollama create`.
