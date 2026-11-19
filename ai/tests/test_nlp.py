from fastapi.testclient import TestClient

from app.main import app
from app.nlp import analyze, count_fillers, extract_keywords, keyword_coverage, long_pauses, speaking_seconds
from tests.helpers import JD

client = TestClient(app)


def test_fillers_single_and_phrases():
    c = count_fillers("Um, so I, uh, built it. You know, it was basically fine. I mean it worked.")
    assert c["um"] == 1 and c["uh"] == 1 and c["basically"] == 1
    assert c["you know"] == 1 and c["i mean"] == 1
    assert c["so"] == 1  # "Um, so" -> "so" right after a comma-pause


def test_like_is_only_a_filler_in_pause_position():
    assert count_fillers("I like Python and I would like to learn Go.")["like"] == 0
    assert count_fillers("It was, like, really slow.")["like"] == 1
    assert count_fillers("So, I started with the schema.")["so"] == 1
    assert count_fillers("so I started with the schema")["so"] == 0


def test_speaking_seconds_prefers_word_span():
    words = [{"word": "a", "start": 1.0, "end": 1.2}, {"word": "b", "start": 4.0, "end": 31.0}]
    assert speaking_seconds(words, 60) == 30.0
    assert speaking_seconds(None, 60) == 60
    assert speaking_seconds([], None) is None


def test_long_pauses():
    words = [
        {"start": 0.0, "end": 0.5},
        {"start": 0.6, "end": 1.0},
        {"start": 3.5, "end": 4.0},  # 2.5 s gap
        {"start": 4.1, "end": 4.5},
    ]
    assert long_pauses(words) == 1


def test_extract_keywords_from_jd():
    kws = extract_keywords(JD)
    for expected in ["postgresql", "docker", "kubernetes", "node.js"]:
        assert expected in kws, kws
    assert "experience" not in kws and "the" not in kws


def test_keyword_coverage_uses_stemming():
    cov, hit, missed = keyword_coverage("I deployed containers with Docker and wrote APIs", ["docker", "api", "kubernetes", "deploy"])
    assert set(hit) == {"docker", "api", "deploy"}  # "APIs"->api, "deployed"->deploy
    assert missed == ["kubernetes"]
    assert cov == 0.75
    assert keyword_coverage("I used Node and Express", ["node.js"])[1] == ["node.js"]


def test_analyze_full():
    text = "Um, I built REST APIs in Node.js. Then I moved the database to PostgreSQL, uh, with Docker."
    words = [{"start": 0.0, "end": 0.3}] + [{"start": 0.4 + i * 0.4, "end": 0.6 + i * 0.4} for i in range(15)]
    m = analyze(text, jd_text=JD, words=words, duration_sec=20)
    assert m.word_count == 17
    assert m.filler_count == 2 and m.fillers == {"um": 1, "uh": 1}
    assert m.speaking_seconds == 6.2
    assert m.wpm == round(17 / (6.2 / 60), 1)
    assert m.sentence_count == 2
    assert "postgresql" in m.keywords_hit and m.keyword_coverage > 0
    assert 0 < m.lexical_diversity <= 1


def test_analyze_empty_transcript():
    m = analyze("", jd_text=JD)
    assert m.word_count == 0 and m.wpm is None and m.filler_count == 0


def test_analyze_endpoint():
    res = client.post("/nlp/analyze", json={"transcript": "Um, I used Docker.", "jd_text": JD, "duration_sec": 3})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["filler_count"] == 1 and "docker" in body["keywords_hit"]
