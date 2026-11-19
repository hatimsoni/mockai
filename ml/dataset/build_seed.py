"""Template-based SEED dataset of interview answers with rubric labels (no LLM needed).

    python ml/dataset/build_seed.py            -> ml/data/seed.csv (~1,200 rows)

Why it exists: the real dataset (LLM-generated answers + human labels, see generate_llm.py and
label.py) needs Ollama and a few hours of labelling. The seed set lets every training script,
test and CI job run offline today.

How it works: each answer is assembled from rubric "components" that we control —
  relevance  0-2  on-topic vs off-topic content
  specifics  0-2  vague words vs named technologies vs technologies + numbers
  star       0-4  how many of Situation / Task / Action / Result sentences are present
  vagueness  0-2  fillers and hedging ("um", "I guess", "not sure")
The label is a weighted sum of the components plus Gaussian noise (real labels are noisy too).

HONESTY NOTE: models trained on this data learn our template rubric, so their scores are
optimistic compared with real answers. Report them as "seed (synthetic)" results.
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "seed.csv"

DOMAINS = {
    "backend": {
        "tech": ["Node.js", "Express", "PostgreSQL", "Redis", "Docker", "Kafka", "GraphQL", "Prisma", "Kubernetes"],
        "systems": ["checkout API", "notification service", "auth service", "billing backend", "search endpoint"],
        "problems": ["timing out under load", "returning stale data", "hard to deploy", "crashing during peak hours"],
        "actions": ["added a {t} cache in front of the database", "split the service and put {t} queues between them",
                    "rewrote the slow queries and added indexes in {t}", "containerised it with {t} and added health checks"],
        "metrics": ["p95 latency dropped from {a} ms to {b} ms", "error rate fell from {a}% to {b}%",
                    "we handled {a}x more requests on the same servers", "deploy time went from {a} minutes to {b}"],
    },
    "frontend": {
        "tech": ["React", "Next.js", "TypeScript", "Tailwind", "React Query", "Vite", "Playwright"],
        "systems": ["dashboard", "signup flow", "product page", "admin panel", "design system"],
        "problems": ["slow on mobile", "full of layout bugs", "hard for new developers to change", "losing users at step two"],
        "actions": ["moved data fetching to the server with {t}", "rebuilt the components in {t} with strict types",
                    "added {t} end-to-end tests for the main flows", "code-split the bundle and lazy loaded routes with {t}"],
        "metrics": ["page load went from {a} s to {b} s", "conversion went up {a}%", "bug reports dropped by {a}%",
                    "Lighthouse score rose from {a} to {b}"],
    },
    "data": {
        "tech": ["Python", "pandas", "scikit-learn", "PyTorch", "Airflow", "SQL", "Spark"],
        "systems": ["churn model", "reporting pipeline", "recommendation feature", "fraud detector", "ETL job"],
        "problems": ["giving wrong numbers", "taking all night to run", "not accurate enough", "breaking every week"],
        "actions": ["rebuilt the features with {t} and added validation checks", "scheduled and monitored it with {t}",
                    "trained a new model in {t} with proper cross-validation", "moved the heavy joins into {t}"],
        "metrics": ["runtime fell from {a} hours to {b}", "precision improved from {a}% to {b}%",
                    "the team saved {a} hours a week", "data incidents dropped from {a} a month to {b}"],
    },
}

QUESTIONS = [
    ("backend", "Tell me about a REST API you designed. What decisions did you make?"),
    ("backend", "How did you improve the performance of a slow backend service?"),
    ("backend", "Describe how you made a system more reliable in production."),
    ("backend", "Walk me through a database schema or query you optimised."),
    ("backend", "How have you used caching or queues in a project?"),
    ("frontend", "Tell me about a frontend performance problem you solved."),
    ("frontend", "How do you structure a large React or Next.js codebase?"),
    ("frontend", "Describe a UI feature you built end to end."),
    ("frontend", "How do you test frontend code?"),
    ("data", "Tell me about a machine learning model you built or improved."),
    ("data", "Describe a data pipeline you worked on and a problem you fixed."),
    ("data", "How do you check that a model or report is giving correct results?"),
    ("behavioral", "Tell me about a time you disagreed with a teammate. What happened?"),
    ("behavioral", "Describe a project that failed or went badly. What did you learn?"),
    ("behavioral", "Tell me about a time you had to deliver under a tight deadline."),
    ("behavioral", "Give an example of when you took ownership of a problem nobody else wanted."),
]

BEHAVIORAL = {
    "situations": ["During a migration at {c}, a teammate and I disagreed on the approach.",
                   "At {c} we had a launch scheduled and two weeks of work left with one week to go.",
                   "At {c}, a feature I led shipped late and customers complained.",
                   "Our on-call rotation at {c} kept getting paged for the same flaky job."],
    "tasks": ["I was responsible for getting us to a decision without damaging the relationship.",
              "My task was to cut scope and still ship something valuable on time.",
              "I needed to find the root cause and make sure it would not happen again.",
              "I volunteered to own the problem end to end."],
    "actions": ["I set up a short call, wrote down both options with pros and cons, and we ran a one-day spike to compare them.",
                "I listed every task, agreed with the product manager on the must-haves, and paired with a junior developer on the riskiest part.",
                "I wrote a blameless post-mortem, added monitoring, and created a checklist for future releases.",
                "I traced the failures, fixed the retry logic, and documented the runbook for the team."],
    "results": ["We picked the faster option, shipped {a}% sooner, and we still work well together.",
                "We launched on time with the core features and added the rest {a} days later.",
                "Similar incidents dropped from {a} a month to {b}, and the checklist is still used.",
                "Pages for that job went from {a} a week to zero."],
}

VAGUE = {
    "situation": ["There was this project at my old job.", "So we had a system.", "I was on a team that did stuff."],
    "task": ["I had to fix some things.", "My job was to make it better.", "I needed to help out."],
    "action": ["I made some changes to the code.", "I worked on it with the team.", "I looked into it and did what was needed."],
    "result": ["It worked out okay in the end.", "It was better after that.", "People were happy with it I think."],
}
FILLERS = ["um,", "uh,", "like,", "basically", "you know,", "I guess", "sort of"]
HEDGES = ["I'm not totally sure but", "I don't really remember the details, but", "maybe"]
COMPANIES = ["a fintech startup", "an e-commerce company", "my last company", "a healthcare SaaS", "an agency"]


def _metric(rng: random.Random, template: str) -> str:
    a = rng.choice([2, 3, 4, 5, 8, 10, 12, 20, 30, 40, 60, 800, 1200])
    b = max(1, a // rng.choice([2, 3, 4, 5]))
    return template.format(a=a, b=b)


def _add_fillers(sentence: str, rng: random.Random, level: int) -> str:
    if level == 0:
        return sentence
    words = sentence.split()
    for _ in range(level):
        words.insert(rng.randrange(len(words) + 1), rng.choice(FILLERS))
    if level == 2 and rng.random() < 0.5:
        words.insert(0, rng.choice(HEDGES))
    return " ".join(words)


def make_answer(question_domain: str, relevance: int, specifics: int, star: int, vagueness: int,
                rng: random.Random) -> str:
    # relevance 0 -> talk about another domain entirely; 1 -> mix of generic + on-topic
    if relevance == 0:
        domain = rng.choice([d for d in DOMAINS if d != question_domain])
    else:
        domain = question_domain
    company = rng.choice(COMPANIES)
    parts = ["situation", "task", "action", "result"]
    present = sorted(rng.sample(range(4), star))  # which STAR parts appear, in order

    sentences = []
    if domain == "behavioral":
        pool = BEHAVIORAL
        for i in present:
            key = parts[i] + "s"
            s = rng.choice(pool[key]).format(c=company, a=rng.choice([20, 30, 40]), b=rng.choice([0, 1]))
            sentences.append(s if specifics > 0 else rng.choice(VAGUE[parts[i]]))
    else:
        d = DOMAINS[domain]
        tech = rng.choice(d["tech"])
        system = rng.choice(d["systems"])
        for i in present:
            p = parts[i]
            if specifics == 0:
                sentences.append(rng.choice(VAGUE[p]))
                continue
            if p == "situation":
                sentences.append(f"At {company}, our {system} was {rng.choice(d['problems'])}.")
            elif p == "task":
                sentences.append(f"I owned fixing the {system} and agreeing the plan with the team.")
            elif p == "action":
                sentences.append("I " + rng.choice(d["actions"]).format(t=tech) + ".")
                if specifics == 2:
                    sentences.append(f"I chose {tech} over {rng.choice(d['tech'])} because it fit our scale and the team knew it.")
            elif p == "result":
                sentences.append(("As a result, " + _metric(rng, rng.choice(d["metrics"])) + ".") if specifics == 2
                                 else "As a result, things got noticeably better.")
    if relevance == 1 and rng.random() < 0.7:
        sentences.insert(0, "That's a good question, I've done a lot of different things in my career.")
    if not sentences:
        sentences = [rng.choice(["I don't think I've done that.", "Not really sure what to say here.", "I would just do my best."])]
    return " ".join(_add_fillers(s, rng, vagueness) for s in sentences)


def rubric_label(relevance: int, specifics: int, star: int, vagueness: int, rng: random.Random) -> int:
    if star == 0:  # no STAR sentence at all -> make_answer produced a non-answer
        relevance = specifics = 0
    score = 1 + 1.4 * relevance / 2 + 1.3 * specifics / 2 + 1.2 * star / 4 - 0.7 * vagueness / 2
    score += rng.gauss(0, 0.35)  # label noise, like disagreement between human raters
    return int(min(5, max(1, round(score))))


def build(n_per_label: int = 240, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    buckets: dict[int, list[dict]] = {k: [] for k in range(1, 6)}
    attempts = 0
    while min(len(b) for b in buckets.values()) < n_per_label and attempts < 200_000:
        attempts += 1
        domain, question = rng.choice(QUESTIONS)
        comps = (rng.randint(0, 2), rng.randint(0, 2), rng.randint(0, 4), rng.randint(0, 2))
        label = rubric_label(*comps, rng)
        if len(buckets[label]) >= n_per_label:
            continue
        buckets[label].append({
            "question": question,
            "answer": make_answer(domain, *comps, rng),
            "label": label,
            "source": "seed-template",
            "intended_score": label,
        })
    rows = [r for b in buckets.values() for r in b]
    rng.shuffle(rows)
    for i, r in enumerate(rows):
        r["id"] = f"seed-{i:05d}"
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-label", type=int, default=240)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    rows = build(args.per_label)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "question", "answer", "label", "source", "intended_score"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
