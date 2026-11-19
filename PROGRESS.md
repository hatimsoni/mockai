# PROGRESS



## Done

- **Phase 0 — setup**: monorepo; FastAPI/Express/Next.js hello-worlds; Prisma schema + init

  migration; Dockerfiles; `infra/docker-compose.yml`; GitHub Actions CI.

- **Phase 1 — upload + RAG**: pypdf → chunking → MiniLM embeddings → Chroma (per session);

  question plan with citations via `invoke_json` (Pydantic + retry + fallback); API auth (JWT,

  bcrypt), repository layer, `POST/GET /sessions`; frontend auth pages, new-interview form,

  interview page with "why this question?" sources.

  Tests: ai 12 pytest, api 9 vitest. Real MiniLM + Chroma smoke-tested locally.

- **Phase 2 — interview UI + ASR**: faster-whisper small/int8 with VAD, word timestamps and a

  filler-preserving prompt (real smoke test: 9 s audio in 3.1 s, fillers kept); audio stored in

  MinIO; API `POST /sessions/:id/answer` + `/finish`; browser recorder hook, TTS question

  reading, interview state machine UI. Tests: ai 15, api 12.
- **Phase 3 — agents + report**: LangGraph graph (Evaluator → Interviewer | Coach) behind
  `POST /interview/step`; Pydantic-validated rubric scores with retry + heuristic fallback;
  follow-up policy (budget 2, RAG-grounded); Coach report with code-computed aggregates; API
  answer/finish routes drive the graph (rollback on failure); report page.
  Tests: ai 27, api 14.



## Pending

- Phases 4–9.



## Known issues

- Docker, Ollama, kind not installed on build machine: compose/images not run locally

  (see `docs/MANUAL_STEPS.md`). LLM paths tested with a fake chat model only.

- Session creation is synchronous (~1 min on CPU with a 7B model).



## Next step

Phase 4: NLP speech analysis — `ai/app/nlp.py` (NLTK): fillers, WPM, pauses, JD keyword
coverage, sentence stats; `/nlp/analyze`; API stores `turn.nlp` before calling the agents.
Output shape must match `NlpMetrics` in `frontend/src/lib/types.ts`.

