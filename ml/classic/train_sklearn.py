"""Classic ML baseline: TF-IDF + Logistic Regression predicting answer quality 1-5.

    python ml/classic/train_sklearn.py

Steps
1. Two trivial baselines (always know what "no skill" scores look like):
   - majority class: always predict the most common label
   - length only: logistic regression on the number of words
2. TF-IDF + LogisticRegression, hyper-parameters picked by 5-fold cross-validation on train.
3. Evaluate everything on the SAME held-out test set; save metrics + the model for the AI service.

Concepts
- TF-IDF: each answer becomes a sparse vector with one dimension per word / word pair (n-gram).
  Weight = term frequency x inverse document frequency, so words common to all answers ("the",
  "I") get low weight and distinctive ones ("latency", "trade-off", "%") get high weight.
- Logistic regression (multinomial): a linear model producing a probability for each class
  via softmax. C = inverse regularisation strength (small C = simpler model, less overfitting).
- Pipeline: vectorizer + model are one object, so the exact same preprocessing runs at
  training and inference (no train/serve skew), and cross-validation can't leak vocabulary.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / "ai"))
from metrics import evaluate  # noqa: E402

from app.quality import model_input  # noqa: E402  same text format as serving (no skew)

DATA = ROOT / "ml" / "data"
RESULTS = ROOT / "ml" / "results"
MODEL_OUT = ROOT / "ai" / "models" / "quality_baseline.joblib"


def text_of(df) -> list[str]:
    """Model input: the answer, prefixed by the question (relevance depends on the question)."""
    return [model_input(q, a) for q, a in zip(df["question"].fillna(""), df["answer"].fillna(""), strict=True)]


def build_pipeline():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, max_features=20000,
                                  token_pattern=r"(?u)\b\w[\w%.+#-]*\b")),  # keep "40%", "node.js", "c++"
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])


def main() -> None:
    import joblib
    import pandas as pd
    from sklearn.dummy import DummyClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GridSearchCV

    train = pd.concat([pd.read_csv(DATA / "train.csv"), pd.read_csv(DATA / "val.csv")])  # CV replaces val here
    test = pd.read_csv(DATA / "test.csv")
    y_train, y_test = train["label"].to_numpy(), test["label"].to_numpy()
    results = {}

    # 1) no-skill baselines
    majority = DummyClassifier(strategy="most_frequent").fit(text_of(train), y_train)
    results["majority_class"] = evaluate(y_test, majority.predict(text_of(test)))

    n_words = lambda df: df["answer"].str.split().str.len().to_numpy().reshape(-1, 1)  # noqa: E731
    length_model = LogisticRegression(max_iter=1000).fit(np.log1p(n_words(train)), y_train)
    results["length_only"] = evaluate(y_test, length_model.predict(np.log1p(n_words(test))))

    # 2) TF-IDF + logistic regression with cross-validated hyper-parameters
    search = GridSearchCV(
        build_pipeline(),
        {"clf__C": [0.3, 1.0, 3.0, 10.0], "tfidf__ngram_range": [(1, 1), (1, 2)]},
        cv=5,
        scoring="neg_mean_absolute_error",
        n_jobs=-1,
    )
    search.fit(text_of(train), y_train)
    best = search.best_estimator_
    results["tfidf_logreg"] = evaluate(y_test, best.predict(text_of(test))) | {"best_params": {
        k: str(v) for k, v in search.best_params_.items()}}

    # most informative words for the extreme classes (explainability)
    vocab = np.array(best.named_steps["tfidf"].get_feature_names_out())
    coefs = best.named_steps["clf"].coef_
    classes = list(best.named_steps["clf"].classes_)
    top = {int(c): vocab[np.argsort(coefs[classes.index(c)])[-12:]][::-1].tolist() for c in (1, 5)}

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "sklearn_metrics.json").write_text(json.dumps({"results": results, "top_words": top,
                                                              "train_rows": len(train), "test_rows": len(test)}, indent=2))
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best, MODEL_OUT)

    for name, m in results.items():
        print(f"{name:16s} acc={m['accuracy']:.3f} macroF1={m['macro_f1']:.3f} MAE={m['mae']:.3f} QWK={m['qwk']:.3f}")
    print("top words for score 5:", top[5])
    print(f"saved model -> {MODEL_OUT}")


if __name__ == "__main__":
    main()
