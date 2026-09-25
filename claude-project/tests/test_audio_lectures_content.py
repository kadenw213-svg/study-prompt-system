from __future__ import annotations

import uuid
from datetime import date

from academic_sync.db import repository
from academic_sync.models.domain import AcademicItem, ChapterTopic, WeeklyLink
from academic_sync.models.enums import CourseStatus, ItemType
from academic_sync.reconciliation.fingerprint import compute_fingerprint
from audio_lectures.content import list_lecture_units


def _weekly_reading(course_id: str, title: str, week_start: date, week_end: date, **kwargs) -> AcademicItem:
    return AcademicItem(
        id=uuid.uuid4().hex,
        course_id=course_id,
        item_type=ItemType.WEEKLY_READING,
        title=title,
        date=week_start,
        date_range_end=week_end,
        is_derived=True,
        fingerprint=compute_fingerprint(
            course_id, "weekly_reading", "Readings", disambiguator=week_start.isoformat()
        ),
        **kwargs,
    )


def test_list_lecture_units_only_includes_weekly_reading_items(session, make_course):
    course = make_course()
    repository.upsert_academic_item(
        session,
        _weekly_reading(course.id, "Chapter 5: Cell Division", date(2026, 9, 7), date(2026, 9, 13)),
    )
    repository.upsert_academic_item(
        session,
        AcademicItem(
            id=uuid.uuid4().hex, course_id=course.id, item_type=ItemType.EXAM,
            title="Exam 1", date=date(2026, 9, 20),
            fingerprint=compute_fingerprint(course.id, "exam", "Exam 1"),
        ),
    )
    units = list_lecture_units(session)
    assert len(units) == 1
    assert units[0].raw_title == "Chapter 5: Cell Division"


def test_list_lecture_units_sorted_by_week_start(session, make_course):
    course = make_course()
    repository.upsert_academic_item(
        session, _weekly_reading(course.id, "Chapter 9", date(2026, 9, 21), date(2026, 9, 27))
    )
    repository.upsert_academic_item(
        session, _weekly_reading(course.id, "Chapter 5", date(2026, 9, 7), date(2026, 9, 13))
    )
    units = list_lecture_units(session)
    assert [u.raw_title for u in units] == ["Chapter 5", "Chapter 9"]


def test_lecture_unit_pulls_saved_chapter_topic_vocabulary(session, make_course):
    course = make_course()
    repository.upsert_academic_item(
        session,
        _weekly_reading(course.id, "Chapter 23: Evolution", date(2026, 8, 24), date(2026, 8, 30)),
    )
    repository.upsert_chapter_topic(
        session,
        ChapterTopic(
            id=uuid.uuid4().hex, course_id=course.id, chapter_label="Chapter 23",
            vocabulary="allele, genotype, phenotype",
            objectives=["Explain genetic drift", "Describe the Hardy-Weinberg principle"],
        ),
    )
    units = list_lecture_units(session)
    assert len(units) == 1
    block = units[0].chapter_blocks[0]
    assert block.label is not None and "Chapter 23" in block.label
    assert "Vocabulary: allele, genotype, phenotype" in block.items
    assert "Explain genetic drift" in block.items


def test_lecture_unit_without_saved_chapter_topic_falls_back_to_bare_label(session, make_course):
    course = make_course()
    repository.upsert_academic_item(
        session,
        _weekly_reading(course.id, "Chapter 1: Intro", date(2026, 8, 17), date(2026, 8, 23)),
    )
    units = list_lecture_units(session)
    block = units[0].chapter_blocks[0]
    assert block.items == []
    header = block.text or block.label or ""
    assert "Chapter 1" in header and "Intro" in header


def test_lecture_unit_carries_weekly_links(session, make_course):
    course = make_course()
    item = _weekly_reading(
        course.id, "Chapter 2", date(2026, 8, 24), date(2026, 8, 30),
        weekly_links=[WeeklyLink(label="Lecture video", url="https://video.example/w2")],
    )
    repository.upsert_academic_item(session, item)
    units = list_lecture_units(session)
    assert units[0].weekly_links == [WeeklyLink(label="Lecture video", url="https://video.example/w2")]


def test_short_title_falls_back_to_raw_title_when_no_chapter_segments(session, make_course):
    course = make_course()
    repository.upsert_academic_item(
        session,
        _weekly_reading(course.id, "Syllabus and Orientation", date(2026, 8, 17), date(2026, 8, 23)),
    )
    units = list_lecture_units(session)
    assert units[0].short_title == "Syllabus and Orientation"


def test_archived_course_excluded_by_default(session, make_course):
    course = make_course()
    repository.upsert_course(session, course.model_copy(update={"status": CourseStatus.ARCHIVED}))
    repository.upsert_academic_item(
        session, _weekly_reading(course.id, "Chapter 1", date(2026, 8, 17), date(2026, 8, 23))
    )
    assert list_lecture_units(session) == []


def test_filter_by_course_code(session, make_course):
    bio = make_course(code="BIO1112")
    che = make_course(code="CHE1011")
    repository.upsert_academic_item(
        session, _weekly_reading(bio.id, "Chapter 1", date(2026, 8, 17), date(2026, 8, 23))
    )
    repository.upsert_academic_item(
        session, _weekly_reading(che.id, "Chapter 1", date(2026, 8, 17), date(2026, 8, 23))
    )
    units = list_lecture_units(session, course_id="CHE1011")
    assert len(units) == 1
    assert units[0].course_code == "CHE1011"
