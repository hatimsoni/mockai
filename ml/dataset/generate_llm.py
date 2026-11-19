"""Generate realistic synthetic answers with the LOCAL LLM (Ollama), one per target score.

    ollama pull qwen2.5:7b-instruct          # once
    python ml/dataset/generate_llm.py --per-score 2      # -> ml/data/llm_raw.csv

For each question x target score 1-5 the LLM writes a spoken-style answer that *should* deserve
that score under our rubric. `intended_score` is the LLM's target, NOT a trusted label: LLMs
miss the target often (a "score 2" answer is frequently a 3). Run label.py afterwards so a
human sets `label`. Only human-labelled rows are used for training (see split.py).

Cost: free. Time: ~20-40 s per answer on CPU with a 7B model -> 16 questions x 5 scores x 2 =
160 answers ≈ 1-1.5 hours. Resumable: existing rows are skipped.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai"))
sys.path.insert(0, str(Path(__file__).parent))
from build_seed import QUESTIONS  # noqa: E402

OUT = ROOT / "ml" / "data" / "llm_raw.csv"
FIELDS = ["id", "question", "answer", "label", "source", "intended_score"]

LEVELS = {
    1: "very poor: off-topic or a non-answer, a few vague sentences, lots of filler words",
    2: "weak: on-topic but vague, no concrete technologies, examples or results, rambling",
    3: "average: relevant with one concrete example but missing either the result or the reasoning",
    4: "good: relevant, specific technologies and decisions, mostly STAR structured, one measurable result",
    5: "excellent: clear STAR structure, concrete decisions with trade-offs, the candidate's own role, numbers for impact, concise",
}

PROMPT = """You are generating training data for an interview-answer scoring model.
Interview question: "{question}"

Write the candidate's SPOKEN answer (as transcribed speech, 60-180 words, first person) that
deserves a score of {score}/5, meaning: {level}.
Make it sound natural for that level (weaker answers may contain "um", "like", hedging).
Vary the candidate's background and details. Output ONLY the answer text, no preamble."""


def main() -> None:
    from langchain_core.messages import HumanMessage

    from app.llm import get_llm

    ap = argparse.ArgumentParser()
    ap.add_argument("--per-score", type=int, default=2, help="answers per question per score")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    existing: set[str] = set()
    if args.out.exists():
        with args.out.open(encoding="utf-8") as f:
            existing = {row["id"] for row in csv.DictReader(f)}
    new_file = not args.out.exists()
    llm = get_llm()  # temperature from LLM_TEMPERATURE; raise it (e.g. 0.9) for more variety

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        for qi, (_, question) in enumerate(QUESTIONS):
            for score in range(1, 6):
                for k in range(args.per_score):
                    rid = f"llm-q{qi:02d}-s{score}-{k}"
                    if rid in existing:
                        continue
                    msg = PROMPT.format(question=question, score=score, level=LEVELS[score])
                    answer = llm.invoke([HumanMessage(content=msg)]).content.strip().strip('"')
                    w.writerow({"id": rid, "question": question, "answer": answer, "label": "",
                                "source": "llm", "intended_score": score})
                    f.flush()
                    print(f"{rid}: {answer[:70]}...")


if __name__ == "__main__":
    main()
