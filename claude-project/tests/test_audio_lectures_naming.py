from __future__ import annotations

from datetime import date
from pathlib import Path

from academic_sync.models.domain import Course
from academic_sync.models.enums import CourseStatus
from audio_lectures.content import ChapterBlock, LectureUnit
from audio_lectures.naming import (
    course_folder_name,
    lecture_filename,
    output_dir_for_course,
    sanitize_filename,
    script_filename,
)


def _unit(**overrides) -> LectureUnit:
    defaults = dict(
        item_id="item-1",
        course_id="course-1",
        course_code="BIO1112",
        course_name="General Biology II",
        is_synthetic=False,
        week_start=date(2026, 9, 7),
        week_end=date(2026, 9, 13),
        module_label="Week 3",
        raw_title="Chapter 5: Cell Division",
        chapter_blocks=[ChapterBlock(label="Chapter 5", text="Cell Division")],
        weekly_links=[],
        fingerprint=None,
    )
    defaults.update(overrides)
    return LectureUnit(**defaults)


def test_sanitize_filename_replaces_forbidden_windows_chars():
    assert sanitize_filename('Chapter 5: Mitosis/Meiosis?') == "Chapter 5 - Mitosis-Meiosis"


def test_sanitize_filename_collapses_whitespace_and_trims_dots():
    assert sanitize_filename("  Too   much   space.  ") == "Too much space"


def test_sanitize_filename_never_returns_empty():
    assert sanitize_filename("???") == "untitled"


def test_sanitize_filename_truncates_long_names():
    long_text = "A" * 300
    result = sanitize_filename(long_text)
    assert len(result) <= 120


def test_course_folder_name_combines_code_and_name():
    course = Course(id="c1", course_code="BIO1112", name="General Biology II", term="Fall 2026")
    assert course_folder_name(course) == "BIO1112 - General Biology II"


def test_course_folder_name_sanitizes_colon_in_course_name():
    course = Course(id="c1", course_code="MAT1340", name="Precalc: Algebra & Trig", term="Fall 2026")
    assert ":" not in course_folder_name(course)


def test_lecture_filename_uses_index_week_and_short_title():
    unit = _unit()
    name = lecture_filename(unit, 3)
    assert name.startswith("03 - Week of Sep 07 - Chapter 5")
    assert name.endswith(".mp3")


def test_lecture_filename_handles_undated_unit():
    unit = _unit(week_start=None)
    name = lecture_filename(unit, 1)
    assert "Undated" in name


def test_script_filename_matches_lecture_filename_stem():
    unit = _unit()
    assert script_filename(unit, 2)[:-4] == lecture_filename(unit, 2)[:-4]
    assert script_filename(unit, 2).endswith(".txt")


def test_output_dir_for_course_creates_directory(tmp_path: Path):
    course = Course(
        id="c1", course_code="CHE1011", name="General Chemistry I", term="Fall 2026",
        status=CourseStatus.ACTIVE,
    )
    result = output_dir_for_course(tmp_path, course)
    assert result.is_dir()
    assert result.name == "CHE1011 - General Chemistry I"
