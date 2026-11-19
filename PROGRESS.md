# PROGRESS

## Done
- **Phase 0 — setup**: monorepo; FastAPI/Express/Next.js hello-worlds; Prisma schema + init
  migration; Dockerfiles; `infra/docker-compose.yml`; GitHub Actions CI.
- **Phase 1 — upload + RAG**: pypdf → chunking → MiniLM embeddings → Chroma (per session);
  question plan with citations via `invoke_json` (Pydantic + retry + fallback); API auth (JWT,
  bcrypt), repository layer, `POST/GET /sessions`; frontend auth pages, new-interview form,
  interview page with "why this question?" sources. Real MiniLM + Chroma smoke-tested locally.
- **Phase 2 — interview UI + ASR**: faster-whisper small/int8 with VAD, word timestamps and a
  filler-preserving prompt (real smoke test: 9 s audio in 3.1 s, fillers kept); audio stored in
  MinIO; API `POST /sessions/:id/answer` + `/finish`; browser recorder hook, TTS question
  reading, interview state machine UI.
- **Phase 3 — agents + report**: LangGraph graph (Evaluator → Interviewer | Coach) behind
  `POST /interview/step`; Pydantic-validated rubric scores with retry + heuristic fallback;
  follow-up policy (budget 2, RAG-grounded); Coach report with code-computed aggregates; API
  answer/finish routes drive the graph (rollback on failure); report page.
- **Phase 4 — NLP**: `ai/app/nlp.py` (NLTK) fillers (pause rule for "like"/"so"), WPM over
  speaking span, long pauses, JD keyword extraction (POS + stopwords) + stemmed coverage,
  sentence stats, lexical diversity; `/nlp/analyze`; JD keywords bias Whisper; API stores
  `turn.nlp` before agents run.
- **Phase 5 — vision**: browser MediaPipe → 45 landmark numbers every 500 ms → `/vision/predict`
  (PyTorch MLP with saved standardisation; heuristic fallback); nose-centred, eye-distance-scaled
  features + yaw/pitch/iris ratios; training with group split + early stopping (synthetic pipeline
  check: acc 0.99 — synthetic only, not installed); recorder script + `/vision-lab` page;
  per-answer attention summary stored on the turn.

Tests now: ai 44 (pytest), api 18 (vitest), frontend 5 (vitest).

## Pending
- Phases 6–9.
- Manual: record webcam data + train attention model (`docs/MANUAL_STEPS.md` §3).

## Known issues
- Docker, Ollama, kind not installed on build machine: compose/images not run locally
  (see `docs/MANUAL_STEPS.md`). LLM paths tested with a fake chat model only.
- Session creation is synchronous (~1 min on CPU with a 7B model).
- MediaPipe WASM/model load from public CDNs (needs internet in the browser).

## Next step
Phase 6: classic ML — `ml/dataset/` (synthetic answer generator via local LLM + template seed
generator + labelling CLI), `ml/classic/train_sklearn.py` (TF-IDF + LogisticRegression) and
`train_keras.py`, metrics table in `ml/results/`; serve baseline via AI `/ml/quality`; API stores
`turn.baselineScore`.
