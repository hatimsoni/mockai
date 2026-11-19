# Architecture

## System
```mermaid
flowchart LR
  subgraph Browser
    UI[Next.js UI<br/>interview · report · dashboard]
    MR[MediaRecorder<br/>webm/opus audio]
    MP[MediaPipe FaceLandmarker<br/>45 numbers / 500 ms]
    TTS[speechSynthesis<br/>reads questions]
  end
  subgraph frontend [frontend · Next.js :3000]
    BFF[/api/* proxy route/]
  end
  subgraph api [api · Express + TS :4000]
    AUTH[JWT auth] --> ROUTES[sessions · interview · attention · dashboard]
    ROUTES --> REPO[Repo interface<br/>Prisma]
  end
  subgraph ai [ai · FastAPI :8000 · stateless]
    RAG[RAG<br/>pypdf → chunks → MiniLM → Chroma]
    AG[LangGraph agents<br/>Interviewer · Evaluator · Coach]
    ASR[faster-whisper small int8]
    NLP[NLTK speech metrics]
    VIS[PyTorch attention MLP]
    ML[scikit-learn baseline<br/>+ optional LoRA scorer]
    AN[Pandas analytics]
  end
  PG[(PostgreSQL)]
  S3[(MinIO / S3)]
  CH[(Chroma on disk)]
  OL[Ollama<br/>qwen2.5:7b-instruct]

  UI --> BFF --> AUTH
  MR --> BFF
  MP --> BFF
  REPO --> PG
  ROUTES -->|HTTP + X-Internal-Key| ai
  RAG --> CH
  ASR --> S3
  RAG --> S3
  AG --> OL
  RAG --> OL
```

## One answer, end to end
```mermaid
sequenceDiagram
  participant B as Browser
  participant A as api
  participant AI as ai
  B->>A: POST /sessions/:id/answer (audio + attention summary)
  A->>AI: /asr/transcribe (+ JD keywords bias)
  AI-->>A: transcript + word timestamps
  par
    A->>AI: /nlp/analyze → fillers, WPM, pauses, keyword coverage
  and
    A->>AI: /ml/quality → scikit-learn baseline score
  end
  A->>A: save transcript, metrics, attention on Turn
  A->>AI: /interview/step (plan + all turns)
  AI->>AI: Evaluator (rubric JSON) → Interviewer (follow-up or next)
  AI-->>A: evaluation + next question
  A-->>B: scored turn + next question (read aloud)
```

## Design principles
- **Free and local first**: every model runs on a 16 GB CPU laptop; hosted services are optional swaps
  (OpenAI-compatible LLM URL, S3 endpoint).
- **Stateless AI service**: the API owns all state in Postgres and sends what each call needs → AI pods
  scale horizontally (except the Chroma disk — see `infra/k8s/apps.yaml`).
- **Privacy**: no video leaves the browser (landmarks only); audio and resumes stay in your own MinIO.
- **Deterministic where possible, LLM where judgement is needed**: NLP metrics, attention, aggregates and
  baselines are code; question writing, scoring prose and coaching are LLM.
- **Graceful degradation**: every LLM step has a validated fallback; optional models (attention MLP, LoRA
  scorer, baseline) are skipped cleanly when absent.
- **Skew guards**: shared feature/prompt/input-format code between training and serving, enforced by tests.

## Data model (Prisma)
`User 1─* InterviewSession 1─* Turn`. A Turn holds the question (+ RAG sources), audio key, transcript,
word timestamps, NLP metrics, attention summary, Evaluator JSON, LLM score and baseline score — all JSON
columns, so new metrics don't need migrations. The session holds the RAG question plan and the Coach report.

## Repository map
| Path | What |
|---|---|
| `frontend/src/app/interviews/[id]/InterviewRoom.tsx` | interview state machine |
| `frontend/src/hooks/` | recorder, TTS, face landmarks, attention batching |
| `api/src/routes/` | auth, sessions, interview loop, dashboard |
| `ai/app/rag/`, `ai/app/agents/` | RAG + LangGraph |
| `ai/app/asr.py`, `nlp.py`, `vision/`, `quality.py`, `analytics.py` | speech, NLP, vision, ML, analytics |
| `ml/` | dataset, baselines, vision training, LoRA notebook, results |
| `infra/` | docker-compose, Kubernetes; CI in `.github/workflows/ci.yml` |
