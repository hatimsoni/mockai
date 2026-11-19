"""Merge seed + human-labelled data and create fixed train / val / test splits.

    python ml/dataset/split.py      -> ml/data/train.csv, val.csv, test.csv

- Stratified by label so every split has the same score distribution.
- Fixed random seed: the SAME test set is used by scikit-learn, Keras and the LoRA notebook,
  so their numbers are directly comparable.
- Exact duplicate answers are dropped first so the same text can't be in train AND test.
"""
from __future__ import annotations

import argparse
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
SEED = 42


def make_splits(df, val_frac: float = 0.15, test_frac: float = 0.15, seed: int = SEED):
    from sklearn.model_selection import train_test_split

    train, rest = train_test_split(df, test_size=val_frac + test_frac, stratify=df["label"], random_state=seed)
    val, test = train_test_split(rest, test_size=test_frac / (val_frac + test_frac), stratify=rest["label"],
                                 random_state=seed)
    return train.reset_index(drop=True), val.reset_index(drop=True), test.reset_index(drop=True)


def main() -> None:
    import pandas as pd

    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA)
    args = ap.parse_args()

    frames = [pd.read_csv(args.data / "seed.csv")]
    labelled = args.data / "labelled.csv"
    if labelled.exists():
        lab = pd.read_csv(labelled).dropna(subset=["label"])
        print(f"adding {len(lab)} human-labelled LLM answers")
        frames.append(lab)
    df = pd.concat(frames, ignore_index=True)
    df["label"] = df["label"].astype(int)
    df = df.drop_duplicates(subset=["answer"])

    train, val, test = make_splits(df)
    for name, part in [("train", train), ("val", val), ("test", test)]:
        part.to_csv(args.data / f"{name}.csv", index=False)
        print(f"{name}: {len(part)} rows, labels {part['label'].value_counts().sort_index().to_dict()}")


if __name__ == "__main__":
    main()
