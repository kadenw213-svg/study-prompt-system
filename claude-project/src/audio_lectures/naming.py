"""Filesystem naming for generated audio lectures.

Layout: `<output_root>/<Course Code - Course Name>/<NN - Week of <date> -
<topic>>.mp3`, with a matching `.txt` script saved alongside each `.mp3`.
Kept as its own module (rather than inlined in cli.py) because it has real
logic worth unit testing: Windows forbids `<>:"/\\|?*` in filenames, and
course/topic text routinely contains ":" (chapter titles) or "/" (date
ranges) that would otherwise silently break path construction.
"""

from __future__ import annotations

import re
from pathlib import Path

from academic_sync.models.domain import Course
from audio_lectures.content import LectureUnit

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')
_MAX_COMPONENT_LEN = 120


def sanitize_filename(text: str) -> str:
    """Replace Windows-forbidden filename characters and collapse
    whitespace. Never silently drops characters that carry real meaning --
    a ":" in a chapter title becomes " -", a "/" becomes "-", so two
    differently-punctuated titles don't collide into the same filename."""
    text = text.replace(":", " -").replace("/", "-")
    text = _INVALID_CHARS.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    if len(text) > _MAX_COMPONENT_LEN:
        text = text[:_MAX_COMPONENT_LEN].rstrip()
    return text or "untitled"


def course_folder_name(course: Course) -> str:
    return sanitize_filename(f"{course.course_code} - {course.name}")


def _base_label(unit: LectureUnit, index: int) -> str:
    date_label = unit.week_start.strftime("%b %d") if unit.week_start else "Undated"
    return sanitize_filename(f"{index:02d} - Week of {date_label} - {unit.short_title}")


def lecture_filename(unit: LectureUnit, index: int) -> str:
    return _base_label(unit, index) + ".mp3"


def script_filename(unit: LectureUnit, index: int) -> str:
    return _base_label(unit, index) + ".txt"


def output_dir_for_course(output_root: Path, course: Course) -> Path:
    path = output_root / course_folder_name(course)
    path.mkdir(parents=True, exist_ok=True)
    return path
