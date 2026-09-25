"""Parsing/canonicalization helpers for chapter/unit topic identity.

A "chapter/unit label" (e.g. "Chapter 23", "Unit 2") is how the system
recognizes that a lecture's title, a weekly reading block's title, and a
saved `ChapterTopic` row are all talking about the same real chapter --
independent of exact wording differences between where each label was
typed. This module is the single place that regex lives; `sync/
calendar_payload.py::_topic_line` and `db/repository.py`'s chapter-topic
lookups both build on it rather than each keeping their own copy.
"""

from __future__ import annotations

import re
from typing import Any

from academic_sync.models.domain import ChapterTopic

# Matches "Chapter N" / "Unit N", optionally followed by ": Topic text".
# The topic text is optional because some real courses (e.g. CHE1011) only
# ever name chapters by number in their source material ("Chapter 1, 2"),
# never with a title -- see CLAUDE.md invariant 25's weekly-reading-blocks
# design and invariant 1 (never fabricate a topic name that isn't there).
CHAPTER_SEGMENT_PATTERN = re.compile(
    r"^(Chapter\s+\d+|Unit\s+\d+)(?:\s*:\s*(.+))?$", re.IGNORECASE
)


def split_chapter_segments(topic: str) -> list[tuple[str | None, str]]:
    """Split a "Chapter N: Topic; Chapter M: Topic" (or bare "Chapter N;
    Chapter M" with no topic text) string into `(label, topic_text)` pairs,
    one per ";"-separated segment. `label` is `None` for a segment that
    doesn't match the chapter/unit pattern at all (e.g. a non-chapter
    administrative segment like "Syllabus and Orientation") -- `topic_text`
    is then the segment verbatim. `topic_text` is `""` when a chapter
    segment has no topic name (the bare "Chapter N" case)."""
    segments = [s.strip() for s in topic.split(";") if s.strip()]
    result: list[tuple[str | None, str]] = []
    for segment in segments:
        match = CHAPTER_SEGMENT_PATTERN.match(segment)
        if match:
            result.append((match.group(1), match.group(2) or ""))
        else:
            result.append((None, segment))
    return result


def canonicalize_chapter_label(label: str) -> str:
    """Stable identity key for a chapter/unit label, independent of exact
    casing/whitespace -- "Chapter 23", "chapter  23" both canonicalize to
    "chapter-23". Falls back to a lowercased/whitespace-collapsed form of
    the whole label for anything that isn't a recognized "Chapter N"/
    "Unit N" shape, so an unusual course-specific label (e.g. a named
    module) still gets a stable, if less structured, key."""
    match = re.match(r"^(chapter|unit)\s+(\d+)", label.strip(), re.IGNORECASE)
    if match:
        return f"{match.group(1).lower()}-{match.group(2)}"
    return re.sub(r"\s+", " ", label.strip().lower())


def build_chapter_topic_blocks(
    segments: list[tuple[str | None, str]],
    topics_by_label: dict[str, ChapterTopic],
) -> list[dict[str, Any]]:
    """Builds one block per chapter segment for a weekly reading block's
    THIS WEEK content -- `topics_by_label` is keyed by
    `canonicalize_chapter_label`. A chapter with a saved `ChapterTopic` row
    gets its real vocabulary/objectives as bulleted items; a chapter
    without one yet (not fabricated -- just not captured) falls back to a
    bare labeled line, same visible chapter name as before, just without
    depth. A non-chapter segment (label is `None`) becomes a plain
    label-less text block, same as `_topic_line` already renders it.

    Returns plain dicts shaped like `sync.calendar_payload.DetailsBlock`'s
    fields (label/text/items) rather than `DetailsBlock` instances --
    deliberately, so this module has no dependency on
    `sync.calendar_payload` (which itself depends on this module for
    chapter-segment parsing, via `_topic_line`). Callers construct
    `DetailsBlock(**d)` for each dict, the same pattern `cli.py::
    render_cmd` already uses for `--details-blocks`."""
    blocks: list[dict[str, Any]] = []
    for label, topic_text in segments:
        if label is None:
            blocks.append({"text": topic_text})
            continue
        # Em dash, not a colon -- format_details_blocks appends its own
        # trailing colon after the label, so "Chapter 23: Topic:" would
        # read as an awkward double colon (see docs/d2l_discovery.md's
        # weekly-reading-blocks section).
        header = f"{label} — {topic_text}" if topic_text else label
        topic = topics_by_label.get(canonicalize_chapter_label(label))
        if topic is None:
            blocks.append({"text": header})
            continue
        items = [f"Vocabulary: {topic.vocabulary}"] if topic.vocabulary else []
        items.extend(topic.objectives)
        if items:
            blocks.append({"label": header, "items": items})
        else:
            blocks.append({"text": header})
    return blocks
