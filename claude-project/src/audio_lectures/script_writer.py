"""Pure text helpers for turning an authored lecture script into TTS-ready
chunks, plus a couple of mechanical sanity checks.

No AI generation happens in this module. The script's actual prose is
authored by whichever Claude Code session runs the /audio-lectures skill
(see docs/style_guide.md for the required voice/structure and the
real-content evidentiary bar) and saved to a plain text file -- this
module only prepares that text for synthesis and estimates its runtime.
"""

from __future__ import annotations

import re

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PLACEHOLDER_PATTERNS = (
    r"\btbd\b",
    r"\btodo\b",
    r"\[insert[^\]]*\]",
    r"\[placeholder\]",
    r"\bfill (this|in) in\b",
)


def chunk_script_for_tts(text: str, max_chars: int = 400) -> list[str]:
    """Splits on paragraph then sentence boundaries so no chunk exceeds
    `max_chars`, without ever cutting a sentence in half -- most local TTS
    engines (Kokoro included) cap how much text one call reliably renders.
    A single sentence longer than max_chars is kept whole rather than
    truncated -- better one oversized chunk than silently dropped words.
    Never merges across a paragraph break, so a natural pause always lands
    at a chunk boundary."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        sentences = _SENTENCE_SPLIT.split(paragraph)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = sentence
        if current:
            chunks.append(current)
            current = ""
    if current:
        chunks.append(current)
    return chunks


def estimate_duration_seconds(text: str, words_per_minute: int = 165) -> float:
    word_count = len(text.split())
    return (word_count / words_per_minute) * 60.0


def validate_script(text: str, min_words: int = 250) -> list[str]:
    """Cheap lint, not a content-quality judge -- flags the two failure
    shapes that are easy to catch mechanically: a script too short to be a
    real lecture, and leftover placeholder text meaning it was never
    finished."""
    warnings: list[str] = []
    word_count = len(text.split())
    if word_count < min_words:
        warnings.append(f"Script is only {word_count} words -- looks incomplete for a full lecture.")
    lowered = text.lower()
    for pattern in _PLACEHOLDER_PATTERNS:
        if re.search(pattern, lowered):
            warnings.append(f"Script appears to contain placeholder text matching /{pattern}/.")
    return warnings
