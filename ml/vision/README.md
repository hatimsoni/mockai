# Attention classifier — data collection and training

The model answers one question per frame: **is the candidate looking at the screen?**
Input: 15 face landmarks (45 numbers) from MediaPipe, captured every 500 ms. Never video.

## Until you train
The AI service uses a rule-based heuristic (head yaw/pitch + iris position). It works for
obvious cases (head turned, looking down at notes). The trained MLP learns *your* setup:
camera angle, glasses, second monitor position.

## How much data to record (and why)
| | Minimum | Good |
|---|---|---|
| Frames per class | 500 (≈ 4 min at 2 fps) | 1,500+ (≈ 12 min) |
| Recordings (sessions) | 3 | 6+ on different days/lighting |
| People | 1 (you) | 3+ if others will use it |

Why: the model has ~2.3k weights; a few thousand varied frames is plenty to fit it without
overfitting. *Variety matters more than volume*: consecutive frames are almost identical, so
10 minutes of staring in one position is worth less than 3 minutes across lighting, distance,
glasses on/off and different "away" directions. We split train/test **by recording**, so you
need ≥ 3 recordings for an honest test score.

## What "looking away" should include
Phone on desk (down), notes left/right, second monitor, window, ceiling (thinking), turned to
talk to someone. Also record "attentive" while *talking* and gesturing — it's an interview.
Keep classes roughly balanced (the loss uses `pos_weight` but balance still helps).

## Option A — in the browser (recommended: same extractor as production)
1. Run the app, sign in, open http://localhost:3000/vision-lab
2. Hold **A** while looking at the screen, hold **L** while looking away. Release = paused.
3. Click **Download CSV** → save into `ml/vision/data/`. Repeat for each session.

## Option B — Python script
```bash
pip install -r ml/requirements.txt
python ml/vision/record_landmarks.py --name yourname
# a = attentive, l = looking away, space = pause, q = quit & save
```

## Train
```bash
cd ai && .venv/Scripts/activate   # torch + scikit-learn live in the AI venv
cd .. && python ml/vision/train_attention.py
```
Prints accuracy / F1 / ROC-AUC on the held-out recordings, writes
`ml/results/attention_metrics.json` and installs `ai/models/attention_mlp.pt`.
Restart the AI service: `/vision/predict` now reports `"model": "mlp"`.

Pipeline check without a webcam: `python ml/vision/train_attention.py --synthetic`
(trains on generated faces, reports metrics, does **not** install the model).

## Privacy
Landmark CSVs are biometric-ish data: they're git-ignored (`ml/vision/data/*.csv`). Don't commit them.
