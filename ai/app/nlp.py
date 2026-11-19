"""Classic NLP speech analytics with NLTK — no LLM, fully deterministic and fast.

Metrics per answer:
- filler words ("um", "uh", "you know"...)        -> nervousness / clarity signal
- words per minute (from Whisper word timestamps) -> pace (120-160 is comfortable)
- long pauses (> 2 s between words)               -> hesitation
- JD keyword coverage                             -> did they speak the job's language?
- sentence-length stats, lexical diversity        -> rambling vs crisp

Concepts:
- Tokenization: splitting text into words/sentences. NLTK's Punkt sentence splitter is a
  trained model that knows "e.g." or "Dr." don't end sentences.
- Stopwords: very common words ("the", "and") that carry little meaning; removed before
  extracting keywords.
- POS tagging: labelling each token's part of speech (noun, verb...). Job keywords are mostly
  nouns ("Kubernetes", "pipelines"), so we keep NN* tags.
- Stemming: chopping words to a root ("deploying", "deployed" -> "deploy") so different forms
  of a keyword still match.
"""
from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

from pydantic import BaseModel

# Single-word fillers that are (almost) always fillers in spoken answers.
FILLERS = {"um", "umm", "uh", "uhh", "uhm", "er", "erm", "ah", "hmm", "mm", "basically", "literally"}
# Multi-word fillers, matched as phrases.
FILLER_PHRASES = ["you know", "i mean", "sort of", "kind of"]
# Ambiguous words: filler only in "pause" position (next to a comma or sentence start).
# "I like Python" -> not a filler. "It was, like, really slow" -> filler.
CONTEXT_FILLERS = {"like", "so", "actually", "right", "okay"}

# Generic job-ad words that are not useful keywords.
JOB_STOPWORDS = {
    "experience", "experiences", "team", "teams", "work", "working", "years", "year", "ability",
    "skills", "skill", "knowledge", "role", "candidate", "company", "requirements", "responsibilities",
    "plus", "strong", "excellent", "good", "understanding", "environment", "opportunity", "job",
    "nice", "level", "degree", "field", "etc", "things", "way", "people", "development", "solutions",
    "engineer", "engineers", "developer", "developers", "hiring", "position", "we",
}

LONG_PAUSE_SEC = 2.0
MAX_KEYWORDS = 15


@lru_cache
def _ensure_nltk() -> None:
    """Download the small NLTK data files on first use (baked into the Docker image)."""
    import nltk

    for pkg, path in [
        ("punkt", "tokenizers/punkt"),
        ("punkt_tab", "tokenizers/punkt_tab"),
        ("stopwords", "corpora/stopwords"),
        ("averaged_perceptron_tagger_eng", "taggers/averaged_perceptron_tagger_eng"),
    ]:
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(pkg, quiet=True)


@lru_cache
def _stopwords() -> frozenset[str]:
    _ensure_nltk()
    from nltk.corpus import stopwords

    return frozenset(stopwords.words("english"))


def _stem(word: str) -> str:
    from nltk.stem import PorterStemmer

    return PorterStemmer().stem(word)


def sentences(text: str) -> list[str]:
    _ensure_nltk()
    from nltk.tokenize import sent_tokenize

    return [s for s in sent_tokenize(text) if s.strip()]


def words_of(text: str) -> list[str]:
    """Lowercase word tokens (keeps tech tokens like node.js, c++, c#)."""
    return re.findall(r"[a-z0-9][a-z0-9+#.]*[a-z0-9+#]|[a-z0-9]", text.lower())


# ---------------- fillers ----------------
def count_fillers(text: str) -> Counter:
    counts: Counter = Counter()
    lowered = text.lower()
    for phrase in FILLER_PHRASES:
        n = len(re.findall(rf"\b{phrase}\b", lowered))
        if n:
            counts[phrase] = n
    # token pass with punctuation kept, so we can see pause positions
    tokens = re.findall(r"[a-z']+|[,.!?;:]", lowered)
    for i, tok in enumerate(tokens):
        if tok in FILLERS:
            counts[tok] += 1
        elif tok in CONTEXT_FILLERS:
            # Whisper writes short pauses as commas: a filler sits next to a pause.
            prev = tokens[i - 1] if i > 0 else ""
            nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
            if prev == "," or nxt == ",":
                counts[tok] += 1
    return counts


# ---------------- pace ----------------
def speaking_seconds(words: list[dict] | None, duration_sec: float | None) -> float | None:
    """Speaking span from first to last word (ignores silence before/after), else duration."""
    if words:
        span = float(words[-1]["end"]) - float(words[0]["start"])
        if span > 0:
            return span
    return duration_sec if duration_sec and duration_sec > 0 else None


def long_pauses(words: list[dict] | None, threshold: float = LONG_PAUSE_SEC) -> int:
    if not words:
        return 0
    return sum(1 for a, b in zip(words, words[1:], strict=False) if float(b["start"]) - float(a["end"]) > threshold)


# ---------------- keywords ----------------
def extract_keywords(jd_text: str, limit: int = MAX_KEYWORDS) -> list[str]:
    """Top JD terms: nouns / tech tokens, minus stopwords, ranked by frequency then position."""
    _ensure_nltk()
    from nltk import pos_tag

    raw_tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9+#.]*[A-Za-z0-9+#]|[A-Za-z0-9]", jd_text)
    tagged = pos_tag(raw_tokens)
    stop = _stopwords() | JOB_STOPWORDS
    counts: Counter = Counter()
    first_seen: dict[str, int] = {}
    for i, (tok, tag) in enumerate(tagged):
        word = tok.lower().rstrip(".")
        is_tech = bool(re.search(r"[0-9+#.]", word)) or (tok[:1].isupper() and i > 0)
        if len(word) < 2 or word in stop or not (tag.startswith("NN") or is_tech):
            continue
        counts[word] += 1
        first_seen.setdefault(word, i)
    ranked = sorted(counts, key=lambda w: (-counts[w], first_seen[w]))
    return ranked[:limit]


def keyword_coverage(answer: str, keywords: list[str]) -> tuple[float, list[str], list[str]]:
    if not keywords:
        return 0.0, [], []
    answer_stems = {_stem(w) for w in words_of(answer)}

    def mentioned(k: str) -> bool:
        base = re.sub(r"\.(js|ts|py)$", "", k)  # "node.js" is said "Node"
        return _stem(k) in answer_stems or _stem(base) in answer_stems or k in answer.lower()

    hit = [k for k in keywords if mentioned(k)]
    missed = [k for k in keywords if k not in hit]
    return round(len(hit) / len(keywords), 3), hit, missed


# ---------------- everything ----------------
class NlpMetrics(BaseModel):
    word_count: int
    speaking_seconds: float | None
    wpm: float | None
    filler_count: int
    fillers_per_min: float | None
    fillers: dict[str, int]
    long_pauses: int
    keyword_coverage: float
    keywords_hit: list[str]
    keywords_missed: list[str]
    sentence_count: int
    avg_sentence_length: float
    max_sentence_length: int
    lexical_diversity: float  # unique words / words (vocabulary richness)


def analyze(transcript: str, jd_text: str = "", words: list[dict] | None = None,
            duration_sec: float | None = None) -> NlpMetrics:
    tokens = words_of(transcript)
    n = len(tokens)
    secs = speaking_seconds(words, duration_sec)
    minutes = secs / 60 if secs else None
    fillers = count_fillers(transcript)
    filler_total = sum(fillers.values())
    sents = sentences(transcript) if transcript.strip() else []
    sent_lens = [len(words_of(s)) for s in sents] or [0]
    cov, hit, missed = keyword_coverage(transcript, extract_keywords(jd_text) if jd_text else [])
    return NlpMetrics(
        word_count=n,
        speaking_seconds=round(secs, 1) if secs else None,
        wpm=round(n / minutes, 1) if minutes and n else None,
        filler_count=filler_total,
        fillers_per_min=round(filler_total / minutes, 2) if minutes else None,
        fillers=dict(fillers.most_common()),
        long_pauses=long_pauses(words),
        keyword_coverage=cov,
        keywords_hit=hit,
        keywords_missed=missed,
        sentence_count=len(sents),
        avg_sentence_length=round(sum(sent_lens) / len(sent_lens), 1),
        max_sentence_length=max(sent_lens),
        lexical_diversity=round(len(set(tokens)) / n, 3) if n else 0.0,
    )
