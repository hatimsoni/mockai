"""Train the attention MLP from recorded CSVs and install it into the AI service.

    python ml/vision/train_attention.py                 # uses ml/vision/data/*.csv
    python ml/vision/train_attention.py --synthetic     # pipeline demo only (NOT installed)

Outputs:
    ai/models/attention_mlp.pt          (loaded automatically by the AI service on restart)
    ml/results/attention_metrics.json   (accuracy / F1 / ROC-AUC on held-out recordings)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai"))
from app.vision.features import RAW_DIM  # noqa: E402
from app.vision.training import train_attention  # noqa: E402

DATA_DIR = Path(__file__).parent / "data"
MODEL_OUT = ROOT / "ai" / "models" / "attention_mlp.pt"
METRICS_OUT = ROOT / "ml" / "results" / "attention_metrics.json"

MIN_FRAMES_PER_CLASS = 500  # see README: below this the model is not trustworthy


def load_csvs(data_dir: Path):
    import pandas as pd

    files = sorted(data_dir.glob("*.csv"))
    if not files:
        sys.exit(f"no CSV files in {data_dir}. Record data first (see ml/vision/README.md).")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    cols = [f"f{i}" for i in range(RAW_DIM)]
    df = df.dropna(subset=cols)
    print(f"{len(files)} files, {len(df)} frames, {df['recording'].nunique()} recordings")
    print(df.groupby("label").size().rename({0: "looking away", 1: "attentive"}).to_string())
    return df[cols].to_numpy(np.float32), df["label"].to_numpy(int), df["recording"].astype(str).to_numpy()


def main() -> None:
    import torch

    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA_DIR)
    ap.add_argument("--synthetic", action="store_true", help="train on fake data to test the pipeline")
    ap.add_argument("--epochs", type=int, default=300)
    args = ap.parse_args()

    if args.synthetic:
        from app.vision.synthetic import make_dataset

        frames, labels, groups = make_dataset(n_per_class=800, n_groups=8)
    else:
        frames, labels, groups = load_csvs(args.data)
        per_class = np.bincount(labels, minlength=2)
        if per_class.min() < MIN_FRAMES_PER_CLASS:
            print(f"WARNING: only {per_class.tolist()} frames per class; aim for >= {MIN_FRAMES_PER_CLASS} each.")
        if len(set(groups)) < 3:
            print("WARNING: fewer than 3 recordings -> test metrics will be unreliable.")

    result = train_attention(frames, labels, groups, epochs=args.epochs)
    print(json.dumps(result.metrics, indent=2))

    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.write_text(json.dumps(result.metrics | {"synthetic": args.synthetic}, indent=2))
    if args.synthetic:
        print("synthetic run: model NOT installed (it would not work on real faces).")
        return
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    torch.save(result.checkpoint, MODEL_OUT)
    print(f"installed {MODEL_OUT} — restart the AI service to load it.")


if __name__ == "__main__":
    main()
