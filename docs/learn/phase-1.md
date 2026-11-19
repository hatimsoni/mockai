# Phase 1 — Resume/JD upload + RAG question generation

## What was built
The user uploads a resume PDF + pastes a JD. The system reads both, stores them as searchable
vectors, and writes interview questions that cite which resume/JD passages they came from.

```mermaid
sequenceDiagram
  participant U as Browser
  participant A as api (Express)
  participant AI as ai (FastAPI)
  participant C as Chroma
  participant L as LLM (Ollama)
  U->>A: POST /sessions (multipart: resume.pdf, jdText, jobTitle)
  A->>A: create InterviewSession row
  A->>AI: POST /documents/ingest (pdf + jd)
  AI->>AI: pypdf -> text -> chunks (~500 chars)
  AI->>C: embed chunks (MiniLM) + store, tagged resume/jd
  A->>AI: POST /questions/plan
  AI->>C: JD chunks; for each, nearest resume chunks
  AI->>L: prompt with [J1].. [R1].. + "cite ids", JSON mode
  L-->>AI: {"questions":[{..., "source_ids":["J1","R2"]}]}
  AI-->>A: questions + real source text
  A->>A: save plan, create Turn #0
  A-->>U: session (first question + "why this question?")
```

## Concepts from zero
- **Embedding**: a neural network turns text into a fixed-length list of numbers (384 for
  all-MiniLM-L6-v2). Texts with similar meaning get vectors pointing in similar directions.
  "Built REST APIs in Express" ≈ "backend services in Node" even without shared words.
- **Cosine similarity**: the angle between two vectors. 1 = same direction (same meaning),
  0 = unrelated. We normalize vectors to length 1 so cosine = dot product.
- **Vector database (Chroma)**: stores vectors + their text + metadata and answers "give me the
  k nearest vectors to this one" fast (HNSW index — a graph you can greedily walk toward the
  nearest neighbours instead of comparing against every vector).
- **Chunking**: one vector per whole resume is too blurry. We split into ~500-char chunks with
  80-char overlap. `RecursiveCharacterTextSplitter` tries `\n\n`, then `\n`, then `. `, then
  spaces, so pieces stay meaningful.
- **RAG (Retrieval-Augmented Generation)**: retrieve relevant text first, paste it into the
  prompt, then generate. Benefits: grounded (fewer hallucinations), personal (uses *your*
  resume), explainable (citations), and no fine-tuning needed when data changes.
- **Retrieval strategy used here**: JD chunks are the "requirements". For each requirement we
  search the resume for the 2 most similar chunks. That pairs "needs Kubernetes" with the
  resume line that mentions Docker/K8s.
- **Citations + validation**: the LLM must return `source_ids`; we map them back to real text
  and *drop ids that don't exist* (the model sometimes invents them).
- **JSON mode + Pydantic + retry** (`ai/app/llm.py`): JSON mode constrains decoding to valid
  JSON; Pydantic validates the shape; on failure we show the model its error and retry; if all
  fails we fall back to template questions so the user is never stuck.
- **Repository pattern (API)**: routes call a `Repo` interface. Prisma implements it in prod,
  an in-memory version in tests → route tests need no database.
- **JWT auth**: login returns a signed token `{sub: userId, exp}`. Each request sends
  `Authorization: Bearer <token>`; the API verifies the signature, no DB lookup needed.
  Passwords are stored as bcrypt hashes (slow + salted).

## Files to read
1. `ai/app/rag/questions.py` — the RAG logic: context gathering, prompt, citation mapping, fallback.
2. `ai/app/rag/store.py` — embeddings + Chroma, one collection per session.
3. `ai/app/llm.py` — `invoke_json`: the reusable "get valid JSON from an LLM" helper.
4. `api/src/routes/sessions.ts` — orchestration + rollback when the AI service fails.
5. `api/src/repo/types.ts` + `tests/sessions.test.ts` — dependency injection for testability.

## Interview questions
1. **What is RAG and why use it here instead of just prompting the LLM?**
   Retrieve relevant passages, then generate with them in the prompt. A bare prompt gives generic
   questions and may invent experience. RAG grounds questions in the actual resume/JD, lets us show
   citations, and works for any new resume instantly — no retraining.
2. **How did you choose chunk size and overlap?**
   ~500 chars ≈ one resume bullet group or JD paragraph: small enough that one vector is about one
   thing, large enough to carry context. 80-char overlap keeps sentences that cross a boundary.
   MiniLM was trained on sentence-length text and truncates at 256 tokens, another reason not to go big.
   Tunable via `CHUNK_SIZE`/`CHUNK_OVERLAP`; I'd evaluate with retrieval hit-rate on labelled pairs.
3. **Why all-MiniLM-L6-v2?**
   Free, local, 22M params (~90 MB), fast on CPU (~thousands of sentences/sec), good quality for
   semantic search. Larger models (bge-large, e5-large) are slightly better but 10× slower on a laptop.
4. **How do you stop the LLM from returning broken JSON or made-up sources?**
   JSON mode at decoding time, Pydantic schema validation, retry with the error message, and a
   deterministic fallback. Source ids are whitelisted against what we actually retrieved.
5. **How is one user's resume kept separate from another's?**
   Each interview gets its own Chroma collection (`session-<id>`); the API only returns sessions where
   `userId` matches the JWT subject, checked in the data layer (`getSession(id, userId)`), so guessing
   another id returns 404.

## Exercises
1. Set `CHUNK_SIZE=150` in `ai/.env`, create an interview, and open "Why this question?". Sources are
   now shorter and more specific — but do questions lose context? Try `1500` and compare.
2. In `gather_context`, change `k=2` to `k=1` and remove the JD loop (just query the resume with the
   job title). Compare the questions: you'll see why matching *per requirement* gives better coverage.
