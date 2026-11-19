# Deployment — free options only, with honest limits

The app is designed to run **locally** (docker-compose or kind). Putting it on the internet for free
is possible, but every free tier trades something away. Free-tier terms change often — check each
provider's current limits before relying on them. Nothing below requires paying; a few require a
card for identity verification (noted).

## What makes this app hard to host for free
| Component | Needs | Problem on free hosting |
|---|---|---|
| Ollama 7B LLM | ~5 GB RAM, several CPU cores | no free PaaS gives this; CPU inference is slow (20–60 s/response) |
| ai service | ~1.5–3 GB RAM (Whisper + MiniLM + torch), disk for Chroma | most free web tiers give 512 MB and sleep |
| Postgres, object storage | persistent | free DB/storage tiers are small but workable |

## Option 1 — One free VM running docker-compose (closest to local)
**Oracle Cloud "Always Free" Ampere A1** (up to 4 ARM cores / 24 GB RAM, as of writing).
1. Create the VM (Ubuntu), open ports 80/443, install Docker.
2. `git clone` the repo, `cp infra/.env.example infra/.env`, set secrets.
3. `docker compose -f infra/docker-compose.yml up -d --build`, pull the model.
4. Put Caddy in front for HTTPS (browsers require HTTPS for mic/camera outside localhost).
Limits: needs a card for verification; free ARM capacity is often "out of stock" in popular regions;
ARM builds of every image are required (all used images are multi-arch); CPU LLM latency stays high;
idle free VMs may be reclaimed — keep backups of the Postgres volume.

## Option 2 — Split across free tiers (no LLM server)
| Piece | Free host | Notes |
|---|---|---|
| frontend (Next.js) | Vercel Hobby or Netlify | Hobby is non-commercial use only |
| api (Express) | Render free web service / Vercel Functions | Render free sleeps after ~15 min idle → ~1 min cold start |
| Postgres | Neon or Supabase free | small storage; Neon scales to zero (cold start on first query) |
| object storage | Cloudflare R2 free tier | S3-compatible: set `S3_ENDPOINT_URL` + keys, boto3 code unchanged |
| ai service | Hugging Face Spaces (Docker, CPU basic) | generous RAM for free; sleeps when idle; public by default; disk is ephemeral → Chroma resets on restart |
| LLM | a free OpenAI-compatible API (e.g. Groq, OpenRouter free models, Google AI Studio) | set `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`; rate limits; your prompts (incl. resume text) leave your machine — read their data policy |
Limits: several cold starts chained together make the first request slow; free LLM APIs have daily/per-minute
caps and may change models; resumes are sent to a third party — say so in the UI if you deploy this publicly.

## Option 3 — Local Kubernetes for demos (kind/minikube)
Not "hosting", but it's the way to *show* Kubernetes skills: `infra/k8s/README.md`. Record the
`kubectl get pods` output and the app running at `localhost:3000` for your portfolio.

## Not recommended for this project
- **Paid managed Kubernetes** (EKS/GKE/AKS) — not free; the spec forbids it.
- **Cloud "free credits"** (one-off trials) — they expire and then bill.
- **Running the 7B model on a 512 MB free instance** — it won't fit.

## Production checklist (if this ever became real)
- HTTPS everywhere; httpOnly cookie sessions instead of localStorage JWT.
- Rate limiting on auth and upload routes; virus scan uploads.
- Background job queue for ingestion/ASR/agents (BullMQ/Redis) instead of synchronous requests.
- Move vectors to pgvector or a Chroma server so the ai service can scale out.
- Backups for Postgres + object storage; data-retention policy for audio and resumes.
- Monitoring: request latency per AI step, LLM fallback rate, evaluator-vs-baseline disagreement.
