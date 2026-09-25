from __future__ import annotations

from academic_sync.chapter_topics import (
    build_chapter_topic_blocks,
    canonicalize_chapter_label,
    split_chapter_segments,
)
from academic_sync.models.domain import ChapterTopic


def test_split_chapter_segments_with_colon_topic():
    assert split_chapter_segments("Chapter 22: Descent with Modification") == [
        ("Chapter 22", "Descent with Modification"),
    ]


def test_split_chapter_segments_bare_chapter_no_topic():
    assert split_chapter_segments("Chapter 1; Chapter 2") == [
        ("Chapter 1", ""),
        ("Chapter 2", ""),
    ]


def test_split_chapter_segments_mixed_chapter_and_plain_text():
    assert split_chapter_segments("Syllabus and Orientation; Chapter 22: Descent with Modification") == [
        (None, "Syllabus and Orientation"),
        ("Chapter 22", "Descent with Modification"),
    ]


def test_split_chapter_segments_unit_label():
    assert split_chapter_segments("Unit 2: Graphs & Functions") == [("Unit 2", "Graphs & Functions")]


def test_canonicalize_chapter_label_normalizes_casing_and_whitespace():
    assert canonicalize_chapter_label("Chapter 23") == "chapter-23"
    assert canonicalize_chapter_label("chapter  23") == "chapter-23"
    assert canonicalize_chapter_label("CHAPTER 23") == "chapter-23"


def test_canonicalize_chapter_label_unit():
    assert canonicalize_chapter_label("Unit 2") == "unit-2"


def test_canonicalize_chapter_label_falls_back_for_unrecognized_shape():
    assert canonicalize_chapter_label("Module 4: Cells") == "module 4: cells"


def _topic(**kwargs) -> ChapterTopic:
    defaults = dict(id="t1", course_id="c1", chapter_label="Chapter 23")
    defaults.update(kwargs)
    return ChapterTopic(**defaults)


def test_build_chapter_topic_blocks_with_saved_topic_includes_vocab_and_objectives():
    segments = [("Chapter 23", "Evolution of Populations")]
    topic = _topic(
        chapter_label="Chapter 23",
        vocabulary="microevolution, genetic drift",
        objectives=["Explain X", "Distinguish Y"],
    )
    blocks = build_chapter_topic_blocks(segments, {"chapter-23": topic})
    assert blocks == [
        {
            "label": "Chapter 23 — Evolution of Populations",
            "items": ["Vocabulary: microevolution, genetic drift", "Explain X", "Distinguish Y"],
        }
    ]


def test_build_chapter_topic_blocks_no_saved_topic_falls_back_to_header_only():
    segments = [("Chapter 26", "Phylogeny and Classification")]
    blocks = build_chapter_topic_blocks(segments, {})
    assert blocks == [{"text": "Chapter 26 — Phylogeny and Classification"}]


def test_build_chapter_topic_blocks_bare_chapter_label_no_topic_text():
    # CHE1011's real chapters are only ever named "Chapter 1"/"Chapter 2" --
    # no invented topic title.
    segments = [("Chapter 1", "")]
    topic = _topic(chapter_label="Chapter 1", objectives=["Read syllabus"])
    blocks = build_chapter_topic_blocks(segments, {"chapter-1": topic})
    assert blocks == [{"label": "Chapter 1", "items": ["Read syllabus"]}]


def test_build_chapter_topic_blocks_non_chapter_segment_is_plain_text():
    segments = [(None, "Syllabus and Orientation")]
    blocks = build_chapter_topic_blocks(segments, {})
    assert blocks == [{"text": "Syllabus and Orientation"}]


def test_build_chapter_topic_blocks_saved_topic_with_no_vocab_or_objectives_falls_back():
    # A ChapterTopic row can exist (discovery looked) but genuinely have
    # nothing real to report yet -- thin but true, not fabricated.
    segments = [("Chapter 5", "Cell Division")]
    topic = _topic(chapter_label="Chapter 5")
    blocks = build_chapter_topic_blocks(segments, {"chapter-5": topic})
    assert blocks == [{"text": "Chapter 5 — Cell Division"}]
