"""Record + label webcam landmark frames for the attention classifier.

    pip install -r ml/requirements.txt
    python ml/vision/record_landmarks.py --name alice

Controls (focus the preview window):
    a      -> label following frames ATTENTIVE   (look at the screen / camera area)
    l      -> label following frames LOOKING AWAY (phone, notes, other monitor, window...)
    space  -> pause (frames not saved)
    q      -> quit and save

Writes ml/vision/data/<name>_<timestamp>.csv with columns:
    recording, label, t_ms, f0..f44   (15 landmarks x (x, y, z), same as the browser sends)

Frames are sampled every 500 ms, exactly like production, so the training data has the same
temporal density as live data. The browser page /vision-lab produces the same CSV format and
uses the *production* JavaScript extractor — prefer it if the Python MediaPipe version gives
slightly different landmarks on your machine.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai"))  # reuse the exact landmark list the model uses
from app.vision.features import KEY_LANDMARKS, RAW_DIM  # noqa: E402

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
MODEL_PATH = Path(__file__).parent / "face_landmarker.task"
DATA_DIR = Path(__file__).parent / "data"
SAMPLE_EVERY_MS = 500


def main() -> None:
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core.base_options import BaseOptions

    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="who is recording (used in the file name)")
    ap.add_argument("--camera", type=int, default=0)
    args = ap.parse_args()

    if not MODEL_PATH.exists():
        print("downloading face_landmarker.task (~4 MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

    landmarker = vision.FaceLandmarker.create_from_options(
        vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
        )
    )

    DATA_DIR.mkdir(exist_ok=True)
    recording = f"{args.name}_{time.strftime('%Y%m%d_%H%M%S')}"
    out_path = DATA_DIR / f"{recording}.csv"
    cap = cv2.VideoCapture(args.camera)
    label: int | None = None  # None = paused
    counts = {0: 0, 1: 0}
    last_sample = 0.0
    start = time.time()

    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["recording", "label", "t_ms"] + [f"f{i}" for i in range(RAW_DIM)])
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            now_ms = int((time.time() - start) * 1000)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), now_ms)
            face = result.face_landmarks[0] if result.face_landmarks else None

            if face and label is not None and now_ms - last_sample >= SAMPLE_EVERY_MS:
                values = [v for _, i in KEY_LANDMARKS for v in (face[i].x, face[i].y, face[i].z)]
                writer.writerow([recording, label, now_ms] + [f"{v:.5f}" for v in values])
                counts[label] += 1
                last_sample = now_ms

            status = {None: "PAUSED (a=attentive, l=looking away)", 1: "ATTENTIVE", 0: "LOOKING AWAY"}[label]
            color = {None: (200, 200, 200), 1: (0, 200, 0), 0: (0, 0, 255)}[label]
            cv2.putText(frame, f"{status}  attentive={counts[1]} away={counts[0]}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            if not face:
                cv2.putText(frame, "no face detected", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.imshow("record landmarks (q to quit)", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("a"):
                label = 1
            elif key == ord("l"):
                label = 0
            elif key == ord(" "):
                label = None

    cap.release()
    cv2.destroyAllWindows()
    print(f"saved {counts[1]} attentive + {counts[0]} away frames to {out_path}")


if __name__ == "__main__":
    main()
