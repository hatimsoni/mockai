"""Speech-to-text with faster-whisper.

Concepts:
- Whisper is an encoder-decoder transformer trained on 680k hours of audio. The encoder
  turns a log-Mel spectrogram (a picture of sound frequencies over time) into features;
  the decoder writes text tokens, like a language model conditioned on audio.
- faster-whisper re-implements Whisper on CTranslate2 with **int8 quantization**: weights
  stored as 8-bit ints instead of 32-bit floats -> ~4x less RAM and 2-4x faster on CPU,
  with almost no accuracy loss. "small" (244M params) is the sweet spot on a laptop.
- **VAD** (voice activity detection, Silero) skips silence, so pauses don't produce
  hallucinated text and decoding is faster.
- **Word timestamps** come from aligning decoder attention to audio frames; we use them
  for words-per-minute and pause analysis in phase 4.
- **initial_prompt**: text the decoder treats as "previous context". Whisper was trained on
  cleaned-up transcripts and tends to *delete* "um"/"uh". A prompt full of fillers makes it
  keep them (we need them to count fillers). Adding JD terms helps spell jargon correctly.
"""
from __future__ import annotations

import os
import tempfile
import threading
from typing import Any

from pydantic import BaseModel

from app.config import get_settings

FILLER_PROMPT = "Umm, let me think like, hmm... Okay, so, uh, here's what I, like, did."

_model: Any = None
_model_override: Any = None
_lock = threading.Lock()  # CTranslate2 models are not safe to *load* concurrently


def set_model_override(model: Any) -> None:
    global _model_override
    _model_override = model


def get_model():
    global _model
    if _model_override is not None:
        return _model_override
    with _lock:
        if _model is None:
            from faster_whisper import WhisperModel

            s = get_settings()
            # First call downloads the weights (~480 MB for "small") into HF_HOME.
            _model = WhisperModel(s.whisper_model, device=s.whisper_device, compute_type=s.whisper_compute_type)
    return _model


class Word(BaseModel):
    word: str
    start: float
    end: float
    probability: float


class Transcript(BaseModel):
    text: str
    language: str
    duration: float  # seconds of audio
    words: list[Word]


def build_prompt(keywords: list[str] | None) -> str:
    terms = ", ".join(keywords[:30]) if keywords else ""
    return f"{FILLER_PROMPT} {terms}".strip()


def transcribe(audio: bytes, keywords: list[str] | None = None, suffix: str = ".webm") -> Transcript:
    model = get_model()
    # faster-whisper decodes via PyAV (bundled FFmpeg), which wants a file path.
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(audio)
        segments, info = model.transcribe(
            path,
            language="en",
            beam_size=1,  # greedy decoding: ~2x faster than beam 5 on CPU, tiny accuracy cost
            vad_filter=True,
            word_timestamps=True,
            initial_prompt=build_prompt(keywords),
            condition_on_previous_text=False,  # avoids repetition loops on long answers
        )
        words: list[Word] = []
        texts: list[str] = []
        for seg in segments:  # a generator: decoding actually happens while iterating
            texts.append(seg.text.strip())
            for w in seg.words or []:
                words.append(Word(word=w.word.strip(), start=round(w.start, 2), end=round(w.end, 2), probability=round(w.probability, 3)))
        return Transcript(
            text=" ".join(t for t in texts if t),
            language=info.language,
            duration=round(float(info.duration), 2),
            words=words,
        )
    finally:
        os.remove(path)
