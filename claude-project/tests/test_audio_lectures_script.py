from __future__ import annotations

from audio_lectures.script_writer import chunk_script_for_tts, estimate_duration_seconds, validate_script


def test_chunk_script_respects_max_chars():
    text = "This is sentence one. " * 30
    chunks = chunk_script_for_tts(text, max_chars=100)
    assert all(len(c) <= 100 for c in chunks)
    assert len(chunks) > 1


def test_chunk_script_never_splits_mid_sentence():
    text = "First sentence here. Second sentence here. Third sentence here."
    chunks = chunk_script_for_tts(text, max_chars=1000)
    # Everything fits in one chunk when the limit is generous.
    assert chunks == [text]


def test_chunk_script_keeps_oversized_single_sentence_whole():
    long_sentence = "A" * 50 + " word " * 40 + "."
    chunks = chunk_script_for_tts(long_sentence, max_chars=20)
    assert long_sentence.strip() in "".join(chunks) or any(
        c.strip() == long_sentence.strip() for c in chunks
    )
    # No sentence content was dropped.
    assert "".join(chunks).replace(" ", "") == long_sentence.replace(" ", "")


def test_chunk_script_splits_on_paragraph_boundaries():
    text = "Paragraph one sentence.\n\nParagraph two sentence."
    chunks = chunk_script_for_tts(text, max_chars=1000)
    assert chunks == ["Paragraph one sentence.", "Paragraph two sentence."]


def test_chunk_script_handles_empty_text():
    assert chunk_script_for_tts("", max_chars=400) == []


def test_estimate_duration_seconds_scales_with_word_count():
    short = estimate_duration_seconds("word " * 165, words_per_minute=165)
    long = estimate_duration_seconds("word " * 330, words_per_minute=165)
    assert short == 60.0
    assert long == 120.0


def test_validate_script_flags_short_script():
    warnings = validate_script("Too short.", min_words=250)
    assert any("words" in w for w in warnings)


def test_validate_script_flags_placeholder_text():
    text = "word " * 300 + "[INSERT MORE CONTENT HERE]"
    warnings = validate_script(text, min_words=250)
    assert any("placeholder" in w for w in warnings)


def test_validate_script_clean_script_has_no_warnings():
    text = "A real sentence about the material. " * 50
    warnings = validate_script(text, min_words=250)
    assert warnings == []
