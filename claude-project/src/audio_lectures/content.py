"""Pulls this project's real curriculum data (courses, WEEKLY_READING
banners, saved chapter topics) into a plain LectureUnit shape the rest of
this skill turns into a narrated script and then audio.

Deliberately read-only against academic_sync's own database, and reuses
its own chapter-segment parser (academic_sync.chapter_topics) rather than
re-implementing "Chapter N: Topic" parsing a second time -- see
CLAUDE.md invariant 26's closing note about chapter_topics.py being the
one place that regex lives. One LectureUnit per WEEKLY_READING item is
the right granularity for "the current weekly curriculum": both real
scraped courses (CLAUDE.md invariant 25) and custom-curriculum synthetic
courses (invariant 35) already funnel their entire weekly content into
that one item type, so this module doesn't need a separate code path for
either.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as _date

from sqlalchemy.orm import Session

from academic_sync.chapter_topics import (
    build_chapter_topic_blocks,
    canonicalize_chapter_label,
    split_chapter_segments,
)
from academic_sync.db import repository
from academic_sync.models.domain import ChapterTopic, WeeklyLink
from academic_sync.models.enums import CourseStatus, ItemType


@dataclass
class ChapterBlock:
    label: str | None
    text: str | None = None
    items: list[str] = field(default_factory=list)


@dataclass
class LectureUnit:
    """One week's worth of real curriculum content for one course --
    exactly the same content a WEEKLY_READING Calendar banner carries,
    repurposed as the source material for one narrated audio lecture."""

    item_id: str
    course_id: str
    course_code: str
    course_name: str
    is_synthetic: bool
    week_start: _date | None
    week_end: _date | None
    module_label: str | None
    raw_title: str
    chapter_blocks: list[ChapterBlock]
    weekly_links: list[WeeklyLink]
    fingerprint: str | None

    @property
    def short_title(self) -> str:
        """A filename/display-friendly stand-in for the week's content --
        the first real chapter/topic label found, or the raw title
        untouched when it doesn't parse into chapter segments at all."""
        for block in self.chapter_blocks:
            if block.label:
                return block.label
        return self.raw_title or "Weekly Overview"

    @property
    def unit_key(self) -> str:
        """Stable manifest key. The item's own id is used rather than
        `fingerprint` -- fingerprint identifies "the same logical week" for
        Calendar reconciliation purposes, but the audio manifest also needs
        to survive a fingerprint being recomputed without losing track of
        already-generated audio for what is, on disk, unambiguously the
        same item row."""
        return self.item_id


def _chapter_blocks_for_title(session: Session, course_id: str, title: str) -> list[ChapterBlock]:
    segments = split_chapter_segments(title) if title else []
    topics_by_label: dict[str, ChapterTopic] = {}
    for label, _text in segments:
        if label is None:
            continue
        topic = repository.get_chapter_topic(session, course_id, label)
        if topic is not None:
            topics_by_label[canonicalize_chapter_label(label)] = topic
    raw_blocks = build_chapter_topic_blocks(segments, topics_by_label)
    return [
        ChapterBlock(label=b.get("label"), text=b.get("text"), items=list(b.get("items", [])))
        for b in raw_blocks
    ]


def list_lecture_units(
    session: Session, course_id: str | None = None, include_inactive: bool = False
) -> list[LectureUnit]:
    """One LectureUnit per real WEEKLY_READING item, across every course
    (or just `course_id` -- accepts either the course's id or its
    course_code), oldest week first within each course. Skips ARCHIVED
    courses always; skips INACTIVE ones unless `include_inactive` -- a
    closed-out past term isn't something you're about to walk-and-listen
    through by default."""
    courses = repository.list_courses(session)
    if course_id:
        courses = [c for c in courses if c.id == course_id or c.course_code == course_id]
    units: list[LectureUnit] = []
    for course in courses:
        if course.status == CourseStatus.ARCHIVED:
            continue
        if course.status == CourseStatus.INACTIVE and not include_inactive:
            continue
        items = [
            item
            for item in repository.list_items_for_course(session, course.id)
            if item.item_type == ItemType.WEEKLY_READING
        ]
        items.sort(key=lambda i: (i.date is None, i.date))
        for item in items:
            blocks = _chapter_blocks_for_title(session, course.id, item.title or "")
            units.append(
                LectureUnit(
                    item_id=item.id,
                    course_id=course.id,
                    course_code=course.course_code,
                    course_name=course.name,
                    is_synthetic=course.is_synthetic,
                    week_start=item.date,
                    week_end=item.date_range_end,
                    module_label=item.module_label,
                    raw_title=item.title or "",
                    chapter_blocks=blocks,
                    weekly_links=list(item.weekly_links),
                    fingerprint=item.fingerprint,
                )
            )
    return units
