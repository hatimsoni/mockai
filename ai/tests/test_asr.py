from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import asr
from app.main import app

client = TestClient(app)


class FakeWhisper:
    """Mimics faster_whisper.WhisperModel.transcribe -> (segments generator, info)."""

    def __init__(self):
        self.kwargs = None

    def transcribe(self, path, **kwargs):
        self.kwargs = kwargs
        words = [
            SimpleNamespace(word=" Um,", start=0.0, end=0.4, probability=0.9),
            SimpleNamespace(word=" I", start=0.5, end=0.6, probability=0.99),
            SimpleNamespace(word=" built", start=0.6, end=0.9, probability=0.98),
            SimpleNamespace(word=" APIs.", start=0.9, end=1.4, probability=0.97),
        ]
        segs = [SimpleNamespace(text=" Um, I built APIs.", words=words)]
        info = SimpleNamespace(language="en", duration=1.5)
        return iter(segs), info


def test_transcribe_maps_words_and_uses_prompt():
    fake = FakeWhisper()
    asr.set_model_override(fake)
    try:
        t = asr.transcribe(b"fake-bytes", keywords=["Kubernetes", "PostgreSQL"])
    finally:
        asr.set_model_override(None)
    assert t.text == "Um, I built APIs."
    assert [w.word for w in t.words] == ["Um,", "I", "built", "APIs."]
    assert t.duration == 1.5
    assert fake.kwargs["word_timestamps"] is True and fake.kwargs["vad_filter"] is True
    assert "Kubernetes" in fake.kwargs["initial_prompt"] and "Umm" in fake.kwargs["initial_prompt"]


def test_transcribe_endpoint():
    asr.set_model_override(FakeWhisper())
    try:
        res = client.post(
            "/asr/transcribe",
            data={"session_id": "s1", "turn_index": "2", "keywords": '["Docker"]'},
            files={"audio": ("answer.webm", b"\x1a\x45\xdf\xa3fake", "audio/webm")},
        )
    finally:
        asr.set_model_override(None)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["text"].startswith("Um")
    assert body["audio_key"] is None  # storage disabled in tests
    assert len(body["words"]) == 4


def test_transcribe_rejects_empty_audio():
    res = client.post("/asr/transcribe", files={"audio": ("a.webm", b"", "audio/webm")})
    assert res.status_code == 400
