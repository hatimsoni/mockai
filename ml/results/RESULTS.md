# Answer-quality scorers — same held-out test set

| Model | Accuracy | Macro-F1 | MAE ↓ | Within ±1 | QWK |
|---|---|---|---|---|---|
| Majority class (no skill) | 0.218 | 0.072 | 1.842 | 0.436 | 0.000 |
| Length only (log words → LogReg) | 0.309 | 0.287 | 1.030 | 0.752 | 0.531 |
| TF-IDF + Logistic Regression | 0.394 | 0.402 | 0.770 | 0.867 | 0.698 |
| Keras embedding + MLP | 0.503 | 0.504 | 0.636 | 0.885 | 0.749 |

Test set: 165 answers (`ml/data/test.csv`, stratified, seed 42).
Data: template seed set (synthetic, rubric-labelled) plus any human-labelled LLM answers — scores on purely synthetic data are optimistic; see `docs/learn/phase-6.md`.
QWK = quadratic weighted kappa (1 = perfect agreement, 0 = chance).
