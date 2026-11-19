"""Small TensorFlow/Keras neural text classifier on the SAME data, for comparison.

    python ml/classic/train_keras.py

Architecture (a "neural bag of words"):
    raw text -> TextVectorization (word ids, max 200 tokens)
             -> Embedding(vocab, 64)       learned 64-d vector per word
             -> GlobalAveragePooling1D     average word vectors -> one vector per answer
             -> Dense(64, relu) -> Dropout(0.3) -> Dense(5, softmax)

Compared with TF-IDF + logistic regression it *learns* word representations instead of using
fixed word counts. With ~1k training answers either can win: on our seed set the Keras model
scores slightly higher (see ml/results/RESULTS.md), partly because template phrases are easy to
memorise. Re-run both on human-labelled data before drawing conclusions.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")  # hide TensorFlow info spam
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from metrics import evaluate  # noqa: E402
from train_sklearn import text_of  # noqa: E402

DATA = ROOT / "ml" / "data"
RESULTS = ROOT / "ml" / "results"


def main() -> None:
    import pandas as pd
    import tensorflow as tf

    tf.keras.utils.set_random_seed(42)
    train, val, test = (pd.read_csv(DATA / f"{s}.csv") for s in ("train", "val", "test"))
    # tf.constant -> tf.string tensor. (np.array(list_of_str) makes a fixed-width "<U..." dtype
    # that Keras 3 rejects.) Shape (n, 1) to match Input(shape=(1,)). Labels shifted to 0..4.
    to_xy = lambda df: (tf.constant(text_of(df))[:, None], df["label"].to_numpy() - 1)  # noqa: E731
    (xtr, ytr), (xva, yva), (xte, yte) = to_xy(train), to_xy(val), to_xy(test)

    vectorize = tf.keras.layers.TextVectorization(max_tokens=10000, output_sequence_length=200)
    vectorize.adapt(xtr[:, 0])  # builds the vocabulary from TRAIN only

    model = tf.keras.Sequential([
        tf.keras.Input(shape=(1,), dtype=tf.string),
        vectorize,
        tf.keras.layers.Embedding(10000, 64, mask_zero=True),
        tf.keras.layers.GlobalAveragePooling1D(),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(5, activation="softmax"),
    ])
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    history = model.fit(
        xtr, ytr,
        validation_data=(xva, yva),
        epochs=60,
        batch_size=32,
        verbose=0,
        callbacks=[tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=6, restore_best_weights=True)],
    )
    probs = model.predict(xte, verbose=0)
    pred = probs.argmax(1) + 1
    metrics = evaluate(yte + 1, pred) | {"epochs": len(history.history["loss"]), "params": int(model.count_params())}

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "keras_metrics.json").write_text(json.dumps({"results": {"keras_embedding_mlp": metrics}}, indent=2))
    print(f"keras  acc={metrics['accuracy']:.3f} macroF1={metrics['macro_f1']:.3f} MAE={metrics['mae']:.3f} "
          f"QWK={metrics['qwk']:.3f} epochs={metrics['epochs']} params={metrics['params']}")


if __name__ == "__main__":
    main()
