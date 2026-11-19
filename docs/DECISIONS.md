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
- **Prisma 6 (not 7)** — Prisma 7 requires driver adapters + `prisma.config.ts`; v6 is simpler to learn and fully supported.
- **`.gitattributes` forces LF** — Dockerfiles and shell scripts run in Linux containers; CRLF breaks them.

## Phase 1 — RAG
- **Question plan generated once up front** — one LLM call (≈30–60 s on CPU) instead of one per question; the Interviewer agent (phase 3) adds follow-ups on top.
- **Per-requirement retrieval (each JD chunk → 2 nearest resume chunks)** — better coverage than a single query with the whole JD, which is dominated by its longest topic.
- **One Chroma collection per session** — simple isolation and cleanup; fine at portfolio scale.
- **Chunk size 500 / overlap 80 chars** — roughly one resume bullet group; MiniLM truncates at 256 tokens anyway.
- **Deterministic fallback questions** — if the LLM is down or keeps returning invalid JSON the user still gets an interview.
- **Repository interface + in-memory implementation in the API** — route tests run without Postgres.
- **JWT in localStorage** — simplest for an SPA-style demo; production would use httpOnly cookies to reduce XSS token theft (noted as a known trade-off).
- **Session creation is synchronous (~1 min)** — simpler than a job queue; a queue (BullMQ/Redis) is the upgrade path.

## Phase 2 — ASR
- **faster-whisper `small` int8, greedy decoding (beam 1)** — ~3 s to transcribe 9 s of speech on a laptop CPU; beam 5 doubles the time for little gain on clear speech.
- **Filler-word `initial_prompt`** — Whisper normally deletes "um/uh"; priming it with a disfluent prompt keeps them (verified locally: "Umm… and uh…" transcribed).
- **Pinned `av>=16,<17`** — root cause of a crash: faster-whisper 1.2.1 passes `metadata_errors=` to `av.open`, which PyAV 17+ removed.
- **Browser speechSynthesis reads questions aloud** — free, no server TTS model needed.
- **Audio recorded as webm/opus via MediaRecorder** — native in Chrome/Edge/Firefox, ~10× smaller than WAV; PyAV decodes it server-side.
- **Next question taken from the RAG plan in phase 2** — the agent graph replaces this in phase 3.

## Phase 3 — agents
- **LangGraph state graph with 3 nodes and conditional edges** — explicit, testable control flow; each agent has one small prompt (more reliable on a 7B model).
- **One graph run per HTTP request, state sent by the API** — no LangGraph checkpointer/DB needed; AI service stays stateless.
- **Overall score = weighted mean computed in Python (relevance .3, depth .3, clarity .2, STAR .2)** — LLMs are bad at arithmetic; formula stays transparent.
- **Interviewer only calls the LLM for follow-ups** — next planned question needs no LLM; keeps CPU latency down.
- **Max 2 follow-ups, never a follow-up of a follow-up, none after a fallback score** — bounded interview length.
- **Coach gets computed numbers and only writes prose** — no hallucinated statistics.
- **Fallbacks everywhere (heuristic evaluation, template follow-up, evaluator-highlight report), flagged in the data** — the interview never dead-ends if Ollama is slow/down; UI marks approximate scores.
- **If the agent step fails, the transcript is rolled back** — the user can just answer again.

## Phase 4 — NLP
- **Rule-based fillers with a comma "pause" rule for ambiguous words (like/so/actually)** — transparent and testable baseline; Whisper renders short pauses as commas.
- **WPM over the speaking span from word timestamps** — doesn't penalise thinking time before the first word.
- **JD keywords = POS-tagged nouns + tech tokens, top 15 by frequency; coverage via Porter stems** — no extra model; `node.js` also matches spoken "Node".
- **Per-answer coverage threshold 20% for "good"** — one answer can't cover a whole JD.
- **Same keyword extractor biases Whisper** — `/asr/transcribe` takes `jd_text`.
- **Removed apt ffmpeg from the AI image** — PyAV wheels bundle FFmpeg.

## Phase 5 — vision
- **MediaPipe FaceLandmarker in the browser, only 45 numbers sent** — privacy, bandwidth, no server GPU.
- **15 key landmarks + 6 engineered features, nose-centred and eye-distance-scaled** — position/scale invariant, explainable.
- **MLP 51→32→16→1 (~2.3k params)** — right-sized for a few thousand frames; trains in seconds on CPU.
- **Rule-based heuristic until a model is trained** — cold start; synthetic-trained models are never shipped.
- **Group split by recording + early stopping** — avoids leakage from near-duplicate consecutive frames.
- **Test diffs the TS and Python landmark lists** — prevents train/serve skew.
- **Browser `/vision-lab` recorder in addition to the Python script** — uses the exact production extractor.
- **Batch 4 frames per request (every ~2 s)** — live feedback without flooding the API.
- **Attention summary computed client-side per answer, validated by zod in the API** — simple; only aggregates stored.
- **MediaPipe WASM + model loaded from public CDNs (jsdelivr, Google storage)** — free; offline use would need copying them into `frontend/public/`.

## Phase 6 — classic ML
- **Template seed dataset with rubric labels + noise** — everything (training, CI, LoRA notebook) runs offline today; clearly labelled synthetic and optimistic.
- **LLM-generated answers are labelled by a human before training** — the LLM's intended score is a hint, not ground truth.
- **Input = question + " [SEP] " + answer, built by `app.quality.model_input`** — relevance depends on the question; one function prevents skew.
- **Metrics: accuracy, macro-F1, MAE, within-1, QWK** — scores are ordinal; QWK is the essay-scoring standard.
- **Majority + length-only baselines reported** — length alone reaches QWK 0.53; shows what the models add.
- **Serve the scikit-learn pipeline, not Keras** — tiny, fast, no TensorFlow in the AI image; Keras is a comparison only.
- **scikit-learn pinned to 1.9.\*** — pickled pipelines are version-sensitive.
- **Baseline used as the Evaluator's fallback** — better than length-only scoring when the LLM is down.
- **`tensorflow-cpu` only in `ml/requirements.txt`** — keeps the AI image ~500 MB lighter.

## Phase 7 — fine-tuning
- **Qwen2.5-0.5B-Instruct + LoRA r=16 on all linear projections, fp16 + GradScaler, 3 epochs** — fits a free T4 and trains in minutes; 0.5B serves on CPU.
- **Hand-written training loop instead of `Trainer`/TRL** — fewer moving parts across library versions, every step visible for study.
- **Score from next-token logits of "1".."5"** — always valid output, deterministic, gives an expected score.
- **Completion-only loss** — learn the score, not the prompt.
- **Notebook generated from `build_notebook.py`; prompt cell generated from `ai/app/scoring_prompt.py`, test-enforced** — reviewable diffs and no prompt skew.
- **CPU smoke run of the notebook (`run_local_smoke.py`)** — first Colab run shouldn't be the first execution.
- **Export GGUF q8_0 + Modelfile with explicit ChatML template; serve via Ollama (`SCORER_MODEL`)** — no transformers/torch-GPU in the AI image.
- **Ruff skips `*.ipynb`** — generated, compact notebook style.

## Phase 8 — dashboard
- **Aggregation in the AI service with Pandas (API sends the user's history)** — metrics are JSON columns; Pandas flattens/aggregates them readably; keeps "analytics" in the Python service.
- **Empty history short-circuits in the API** — no AI round-trip for new users.
- **recharts, one y-axis per chart, fixed validated palette order, legend + direct labels, tooltips, table toggle** — honest, accessible charts; no dual axes.
- **Rule-based recommendations from aggregates** — deterministic and explainable; the Coach agent already gives per-interview LLM advice.
- **Charts loaded with `next/dynamic` (`ssr: false`)** — recharts measures the DOM.

## Phase 9 — Kubernetes, CI/CD, docs
- **Plain YAML + kustomize (no Helm)** — fewer concepts to learn; kustomize ships with kubectl.
- **Postgres as StatefulSet; MinIO/Ollama/ai as single-replica Deployments with `Recreate` + RWO PVCs** — honest about what is stateful.
- **api and frontend run 2 replicas** — stateless; shows horizontal scaling. Prisma's migration advisory lock makes concurrent `migrate deploy` safe.
- **Bucket creation and model download as Jobs** — idempotent one-shot tasks with retries.
- **Secret template only; real secret applied out-of-band and git-ignored** — no secrets in git, even base64.
- **Images loaded with `kind load` (`:local`, `IfNotPresent`)** — no registry account needed.
- **CI validates manifests with kubeconform + kind `--dry-run=server`** — real admission checks without pulling multi-GB images.
- **Whisper weights cache is ephemeral in k8s** (HF_HOME holds the baked MiniLM model) — re-downloads ~480 MB after a pod restart; acceptable for local demos.
- **Free deployment documented, not automated** — every option needs an account and has sleep/RAM/rate limits; local stays the primary target.
