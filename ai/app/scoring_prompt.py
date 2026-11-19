"""The ONE prompt used to train (LoRA notebook) and serve (Ollama SCORER_MODEL) the fine-tuned scorer.

The notebook ml/finetune/lora_qwen_scoring.ipynb contains an exact copy of SYSTEM and
USER_TEMPLATE; ai/tests/test_finetuned.py fails if they ever drift apart. A model fine-tuned on
one prompt and queried with another loses most of what it learned (prompt skew).
"""

SYSTEM = "You are an interview coach. Score the candidate's answer from 1 (very poor) to 5 (excellent). Reply with a single digit."

USER_TEMPLATE = """Rubric: 1 off-topic or non-answer; 2 on-topic but vague; 3 one concrete example but missing result or reasoning; 4 specific and structured with a measurable result; 5 clear STAR structure, decisions with trade-offs, own role, quantified impact.

Question: {question}
Answer: {answer}

Score (1-5):"""


def build_messages(question: str, answer: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER_TEMPLATE.format(question=question, answer=answer)},
    ]
