from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from academic_sync.cli import app
from academic_sync.db.migrations import run_migrations
from academic_sync.db.session import get_engine, reset_engine_cache
from academic_sync.sync.ics_export import IcsEvent, _fold, build_ics, html_to_text

runner = CliRunner()
CRLF_FOLD = "\r\n "


def _isolated_db(tmp_path: Path) -> None:
    reset_engine_cache()
    os.environ["ACADEMIC_SYNC_DB_PATH"] = str(tmp_path / "test.db")
    from academic_sync.config import clear_caches

    clear_caches()
    run_migrations(get_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}"))


def _add_synthetic_course() -> str:
    result = runner.invoke(app, [
        "course", "add", "--code", "LINALG", "--name", "Linear Algebra", "--term", "Self-study",
        "--start", "2026-09-28", "--end", "2026-10-18", "--synthetic",
    ])
    assert result.exit_code == 0, result.stdout
    return result.stdout.strip().split("id=")[-1]


def _payload(summary: str, start: dict, end: dict, description: str = "<b>X</b><br>y") -> dict:
    return {"summary": summary, "description": description, "start": start, "end": end}


def test_ics_is_deterministic_and_has_no_attendees():
    events = [
        IcsEvent("b@x", _payload("Due", {"dateTime": "2026-10-04T23:59:00", "timeZone": "America/Denver"},
                                 {"dateTime": "2026-10-05T00:00:00", "timeZone": "America/Denver"})),
        IcsEvent("a@x", _payload("Week", {"date": "2026-09-28"}, {"date": "2026-10-05"})),
    ]
    stamp = datetime(2026, 9, 28, tzinfo=UTC)
    first = build_ics("Linear Algebra", events, dtstamp=stamp)
    second = build_ics("Linear Algebra", list(reversed(events)), dtstamp=stamp)
    assert first == second
    assert "ATTENDEE" not in first and "ORGANIZER" not in first and "CONFERENCE" not in first
    assert "DTSTART;VALUE=DATE:20260928" in first
    assert "DTEND;VALUE=DATE:20261005" in first
    assert "DTSTART:20261005T055900Z" in first  # 23:59 MDT -> UTC
    assert first.index("UID:a@x") < first.index("UID:b@x")  # sorted by start
    assert first.endswith("\r\n")


def test_ics_escapes_and_folds_long_lines():
    long_desc = "<b>THIS WEEK</b><br>" + "; ".join(f"Chapter {i}: Topic, part" for i in range(20))
    text = build_ics("C", [IcsEvent("u@x", _payload("S", {"date": "2026-09-28"},
                                                          {"date": "2026-09-29"}, long_desc))],
                     dtstamp=datetime(2026, 9, 28, tzinfo=UTC))
    for physical in text.split("\r\n"):
        assert len(physical.encode("utf-8")) <= 75
    unfolded = text.replace(CRLF_FOLD, "")
    assert "Chapter 1: Topic\\, part\\; Chapter 2" in unfolded
    assert "DESCRIPTION:THIS WEEK\\nChapter 0" in unfolded


def test_fold_never_splits_multibyte_characters():
    line = "SUMMARY:" + "–" * 60
    for physical in _fold(line).split("\r\n"):
        physical.encode("utf-8").decode("utf-8")
        assert len(physical.encode("utf-8")) <= 75


def test_html_to_text_keeps_links():
    assert html_to_text('<b>LINKS</b><br><a href="https://e.x/a">Slides</a>') == (
        "LINKS\nSlides (https://e.x/a)"
    )


def test_export_ics_cli_round_trip_with_chapter_depth(tmp_path):
    _isolated_db(tmp_path)
    course_id = _add_synthetic_course()
    for start, end, chapter in (
        ("2026-09-28", "2026-10-04", "Chapter 1: Vectors"),
        ("2026-10-05", "2026-10-11", "Chapter 2: Matrices"),
    ):
        assert runner.invoke(app, [
            "weekly-reading-add", "--course", course_id, "--week-start", start,
            "--week-end", end, "--chapters", chapter,
        ]).exit_code == 0
    assert runner.invoke(app, [
        "chapter-topic-add", "--course", course_id, "--chapter", "Chapter 1", "--title", "Vectors",
        "--vocabulary", "vector, scalar, span", "--objective", "Add vectors geometrically",
        "--objective", "Describe the span of two vectors",
    ]).exit_code == 0
    out = tmp_path / "courses" / "linalg.ics"
    result = runner.invoke(app, ["export-ics", "--course", course_id, "--out", str(out)])
    assert result.exit_code == 0, result.stdout
    first = out.read_bytes()
    runner.invoke(app, ["export-ics", "--course", course_id, "--out", str(out)])
    assert out.read_bytes() == first
    text = first.decode("utf-8").replace(CRLF_FOLD, "")
    assert text.count("BEGIN:VEVENT") == 2
    assert text.count("SUMMARY:LINALG Weekly Overview") == 2
    assert "SYNTHESIZED CURRICULUM" in text
    assert "Chapter 1 — Vectors:" in text
    assert "Describe the span of two vectors" in text
    assert "@study-prompt-system" in text
    assert "ATTENDEE" not in text
