"""Collect every *_metrics.json in ml/results/ into one markdown table: ml/results/RESULTS.md

    python ml/results/compare.py

Sources: sklearn_metrics.json (phase 6), keras_metrics.json (phase 6),
lora_metrics.json (phase 7, produced by the Colab notebook — copy it here).
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
ORDER = ["majority_class", "length_only", "tfidf_logreg", "keras_embedding_mlp", "qwen_base_zero_shot", "qwen_lora"]
NAMES = {
    "majority_class": "Majority class (no skill)",
    "length_only": "Length only (log words → LogReg)",
    "tfidf_logreg": "TF-IDF + Logistic Regression",
    "keras_embedding_mlp": "Keras embedding + MLP",
    "qwen_base_zero_shot": "Qwen2.5-0.5B-Instruct, zero-shot",
    "qwen_lora": "Qwen2.5-0.5B-Instruct + LoRA",
}


def main() -> None:
    rows: dict[str, dict] = {}
    for f in sorted(HERE.glob("*_metrics.json")):
        if f.name == "attention_metrics.json":
            continue
        rows.update(json.loads(f.read_text()).get("results", {}))
    lines = [
        "# Answer-quality scorers — same held-out test set",
        "",
        "| Model | Accuracy | Macro-F1 | MAE ↓ | Within ±1 | QWK |",
        "|---|---|---|---|---|---|",
    ]
    for key in ORDER + sorted(set(rows) - set(ORDER)):
        if key in rows:
            m = rows[key]
            lines.append(f"| {NAMES.get(key, key)} | {m['accuracy']:.3f} | {m['macro_f1']:.3f} | {m['mae']:.3f} | "
                         f"{m['within_1']:.3f} | {m['qwk']:.3f} |")
    n = next(iter(rows.values()))["n"] if rows else 0
    lines += [
        "",
        f"Test set: {n} answers (`ml/data/test.csv`, stratified, seed 42).",
        "Data: template seed set (synthetic, rubric-labelled) plus any human-labelled LLM answers — "
        "scores on purely synthetic data are optimistic; see `docs/learn/phase-6.md`.",
        "QWK = quadratic weighted kappa (1 = perfect agreement, 0 = chance).",
    ]
    (HERE / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
