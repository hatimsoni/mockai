"""Manual labelling CLI: you are the ground truth.

    python ml/dataset/label.py                 # labels ml/data/llm_raw.csv -> ml/data/labelled.csv

For each unlabelled answer: shows the question, the answer and the LLM's intended score.
Type 1-5 to set the label, ENTER to accept the intended score, s to skip, q to save and quit.
Progress is saved after every answer, so you can stop any time.

Rubric (keep it consistent!):
  1 off-topic / non-answer      2 on-topic but vague, no example
  3 one concrete example, missing result or reasoning
  4 specific, structured, one measurable result
  5 clear STAR, decisions + trade-offs, own role, quantified impact, concise
Tip: label in one sitting per ~50 answers and re-label 10 random ones later to check your own
consistency (intra-rater agreement).
"""
from __future__ import annotations

import argparse
import csv
import textwrap
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
FIELDS = ["id", "question", "answer", "label", "source", "intended_score"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DATA / "llm_raw.csv")
    ap.add_argument("--out", type=Path, default=DATA / "labelled.csv")
    args = ap.parse_args()

    with args.src.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    done: dict[str, dict] = {}
    if args.out.exists():
        with args.out.open(encoding="utf-8") as f:
            done = {r["id"]: r for r in csv.DictReader(f)}

    todo = [r for r in rows if r["id"] not in done]
    print(f"{len(done)} labelled, {len(todo)} to go. Keys: 1-5, ENTER=accept intended, s=skip, q=quit\n")

    def save() -> None:
        with args.out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(done.values())

    for i, r in enumerate(todo, 1):
        print("=" * 80)
        print(f"[{i}/{len(todo)}] Q: {r['question']}")
        print(textwrap.fill(r["answer"], 80))
        key = input(f"label (intended {r['intended_score']}): ").strip().lower()
        if key == "q":
            break
        if key == "s":
            continue
        if key == "":
            key = r["intended_score"]
        if key not in {"1", "2", "3", "4", "5"}:
            print("  ! type 1-5, ENTER, s or q — skipped")
            continue
        done[r["id"]] = {**r, "label": key}
        save()
    save()
    print(f"saved {len(done)} labelled rows to {args.out}")


if __name__ == "__main__":
    main()
