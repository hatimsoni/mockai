# PROGRESS

## Status: all phases (0–9) built. Remaining work is manual (see Pending).

## Done
- **Phase 0 — setup**: monorepo; FastAPI/Express/Next.js; Prisma schema + init migration; Dockerfiles;
  `infra/docker-compose.yml`; GitHub Actions CI.
- **Phase 1 — upload + RAG**: pypdf → chunking → MiniLM → Chroma (per session); question plan with
  citations via `invoke_json` (Pydantic + retry + fallback); JWT auth; repository layer; sessions API;
  auth pages, upload form, "why this question?" sources. Real MiniLM + Chroma smoke-tested.
- **Phase 2 — interview UI + ASR**: faster-whisper small/int8, VAD, word timestamps, filler-preserving
  prompt (real smoke test: 9 s audio → 3.1 s, fillers kept); audio in MinIO; recorder + TTS UI.
- **Phase 3 — agents + report**: LangGraph (Evaluator → Interviewer | Coach), rubric JSON with retries
  and fallbacks, follow-up policy, Coach report, report page.
- **Phase 4 — NLP**: NLTK fillers (pause rule), WPM, pauses, JD keywords (POS + stemming), sentence stats.
- **Phase 5 — vision**: browser MediaPipe → 45 numbers/500 ms → PyTorch MLP (heuristic until trained);
  group-split training; recorder script + `/vision-lab`; per-answer attention summary.
- **Phase 6 — classic ML**: seed dataset + LLM generator + labelling CLI; sklearn + Keras baselines;
  `ml/results/RESULTS.md`; `/ml/quality`; baseline score stored and used as Evaluator fallback.
- **Phase 7 — LoRA**: Colab notebook (generated, prompt test-enforced), logit scoring, base vs LoRA on the
  shared test set, GGUF + Modelfile export; CPU smoke run passed; optional `SCORER_MODEL`.
- **Phase 8 — dashboard**: Pandas analytics (`/analytics/progress`), `GET /dashboard`, recharts page.
- **Phase 9 — k8s + docs**: `infra/k8s/` (kustomize, StatefulSet, Jobs, probes, limits, kind config);
  CI `k8s` job (kubeconform + kind server-side dry run); ARCHITECTURE, SETUP, DEPLOYMENT, README.

Tests: ai 56 + ml 5 (pytest), api 22 (vitest), frontend 5 (vitest). All lint/typecheck/build clean.

## Pending (manual — exact steps in `docs/MANUAL_STEPS.md`)
1. §1–2 Install Docker/Ollama, run the stack end to end with the real LLM (never run on the build machine).
2. §3 Record webcam data and train the attention model.
3. §4 Generate + label real answers, retrain baselines.
4. §5 Run the LoRA notebook on Colab, copy `lora_metrics.json`, update README table.
5. §6 Run on kind; §7 demo GIF + screenshots; confirm CI is green on GitHub.

## Known issues / limits
- Docker, Ollama and kind were not available on the build machine: compose, images and k8s were not
  executed locally (k8s validated in CI only). LLM paths are unit-tested with fake models; the first
  real end-to-end run may need prompt tuning for the 7B model.
- Session creation and answer scoring are synchronous (tens of seconds on CPU with a 7B model).
- MediaPipe WASM/model load from public CDNs (browser needs internet).
- Seed dataset is synthetic → baseline metrics optimistic.
- JWT in localStorage (documented trade-off; httpOnly cookies for production).

## Next step
Run `docs/MANUAL_STEPS.md` §2 (Docker first run) and fix anything the real LLM/containers surface.
Good follow-ups: background job queue (BullMQ) for ASR/agents, pgvector instead of Chroma for scale-out,
httpOnly cookie auth, per-question model-answer examples in the report.
