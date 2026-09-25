"""CLI entry point.

This CLI is the deterministic half of the system: parsing, extraction,
completeness, reconciliation, preferences, and the local database. It does
not talk to D2L or Google Calendar on its own -- see README.md and
docs/architecture.md for why that's handled live by the academic-import
skill instead. `plan`/`sync` here operate purely on already-ingested local
state.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from sqlalchemy.orm import Session

from academic_sync import completeness as completeness_mod
from academic_sync import diagnostics as diagnostics_mod
from academic_sync import preferences as prefs_mod
from academic_sync.chapter_topics import (
    build_chapter_topic_blocks,
    canonicalize_chapter_label,
    split_chapter_segments,
)
from academic_sync.config import REPO_ROOT, get_config
from academic_sync.db import repository
from academic_sync.db.migrations import run_migrations
from academic_sync.db.session import get_engine, session_scope
from academic_sync.extraction.pipeline import (
    EXTRACTION_VERSION,
    ExtractionContext,
    extract_from_document,
)
from academic_sync.models.domain import (
    AcademicItem,
    ChapterTopic,
    Course,
    CourseGradeSnapshot,
    GradeSnapshot,
    Source,
    UnresolvedReference,
    WeeklyLink,
)
from academic_sync.models.enums import (
    CourseStatus,
    DiagnosticStatus,
    ItemStatus,
    ItemType,
    SourceType,
    SyncAction,
    UnresolvedReferenceKind,
)
from academic_sync.parsers.base import ParsedDocument
from academic_sync.parsers.html_parser import parse_html
from academic_sync.parsers.pdf_parser import parse_pdf
from academic_sync.reconciliation.engine import snapshot_compared_fields
from academic_sync.reconciliation.fingerprint import compute_fingerprint
from academic_sync.reporting.formatters import (
    format_completeness_report,
    format_course_export,
    format_plan_detail,
    format_plan_summary,
    format_unresolved,
)
from academic_sync.sync.calendar_payload import (
    DetailsBlock,
    DiagnosticAssignment,
    DiagnosticCourseSection,
    LocationInfo,
    build_deadline_description,
    build_event_payload,
    build_meeting_description,
    build_weekly_diagnostic_description,
    build_weekly_diagnostic_payload,
    build_weekly_reading_description,
    format_details_blocks,
    platform_label_for_source,
)
from academic_sync.sync.ics_export import IcsEvent, build_ics
from academic_sync.sync.planner import compute_plan

app = typer.Typer(help="academic-sync: D2L -> normalized academic model -> Google Calendar.")
course_app = typer.Typer(help="Manage known courses.")
prefs_app = typer.Typer(help="Manage reusable preferences.")
app.add_typer(course_app, name="course")
app.add_typer(prefs_app, name="prefs")

console = Console()


# --------------------------------------------------------------------------
# db
# --------------------------------------------------------------------------

@app.command("db-init")
def db_init() -> None:
    """Create/upgrade the local SQLite database."""
    version = run_migrations(get_engine())
    console.print(f"[green]Database ready.[/green] Schema version {version}.")


# --------------------------------------------------------------------------
# courses
# --------------------------------------------------------------------------

@course_app.command("add")
def course_add(
    code: Annotated[str, typer.Option("--code")],
    name: Annotated[str, typer.Option("--name")],
    term: Annotated[str, typer.Option("--term")],
    section: Annotated[str | None, typer.Option("--section")] = None,
    instructor: Annotated[str | None, typer.Option("--instructor")] = None,
    instructor_contact: Annotated[str | None, typer.Option("--instructor-contact")] = None,
    campus: Annotated[str | None, typer.Option("--campus")] = None,
    start: Annotated[str | None, typer.Option("--start", help="YYYY-MM-DD")] = None,
    end: Annotated[str | None, typer.Option("--end", help="YYYY-MM-DD")] = None,
    d2l_id: Annotated[str | None, typer.Option("--d2l-id")] = None,
    d2l_url: Annotated[str | None, typer.Option("--d2l-url")] = None,
    delivery: Annotated[str | None, typer.Option("--delivery")] = None,
    synthetic: Annotated[
        bool,
        typer.Option(
            "--synthetic",
            help="Flag this as a self-directed, fully AI-authored curriculum with no real "
            "D2L/instructor source -- see CLAUDE.md invariant 35 and "
            ".claude/skills/custom-curriculum/SKILL.md. Never set this for a real scraped "
            "course.",
        ),
    ] = False,
) -> None:
    """Register a course discovered during D2L scanning."""
    course = Course(
        id=uuid.uuid4().hex,
        course_code=code,
        section=section,
        name=name,
        term=term,
        instructor=instructor,
        instructor_contact=instructor_contact,
        campus=campus,
        start_date=date.fromisoformat(start) if start else None,
        end_date=date.fromisoformat(end) if end else None,
        d2l_identifier=d2l_id,
        d2l_url=d2l_url,
        delivery_format=delivery,
        status=CourseStatus.ACTIVE,
        is_synthetic=synthetic,
    )
    with session_scope() as session:
        row = repository.upsert_course(session, course)
        repository.log_audit_event(
            session, event_type="course_registered", course_id=row.id,
            summary=f"Registered {code} ({term})",
        )
    console.print(f"[green]Course registered.[/green] id={row.id}")


@app.command("courses")
def list_courses_cmd(term: Annotated[str | None, typer.Option("--term")] = None) -> None:
    with session_scope() as session:
        courses = repository.list_courses(session, term=term)
    if not courses:
        console.print("No courses registered yet. Use `academic-sync course add`.")
        return
    table = Table(show_header=True)
    for col in ["id", "code", "section", "name", "term", "status", "synthetic"]:
        table.add_column(col)
    for c in courses:
        table.add_row(
            c.id[:8], c.course_code, c.section or "-", c.name, c.term, c.status.value,
            "yes" if c.is_synthetic else "-",
        )
    console.print(table)


# --------------------------------------------------------------------------
# extract
# --------------------------------------------------------------------------

def _strip_get_page_text_header(text: str) -> tuple[str, str | None]:
    """Strip claude-in-chrome's get_page_text metadata header if present.

    That tool prefixes its output with `Title: ...` / `URL: ...` /
    `Source element: ...` lines followed by a bare `---` separator before
    the actual page content. If the academic-import skill saves that raw
    output straight to a scratch file for `extract`, the title line (e.g.
    "Title: Quiz List - BIO1112...") would otherwise get classified as an
    obligation with no date on every single course scan -- a real,
    recurring false positive, not a one-off. Leaves text untouched if the
    header shape isn't present.
    """
    lines = text.splitlines()
    if not lines or not lines[0].startswith("Title:"):
        return text, None
    title = lines[0][len("Title:") :].strip()
    for i, line in enumerate(lines[1:6], start=1):
        if line.strip() == "---":
            return "\n".join(lines[i + 1 :]), title
    return text, None


def _load_document(path: Path, title: str | None) -> ParsedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(str(path), base_title=title)
    if suffix in (".html", ".htm"):
        return parse_html(path.read_text(encoding="utf-8", errors="replace"), base_title=title)
    text = path.read_text(encoding="utf-8", errors="replace")
    cleaned_text, extracted_title = _strip_get_page_text_header(text)
    return ParsedDocument(text=cleaned_text, title=title or extracted_title)


@app.command("extract")
def extract_cmd(
    path: Annotated[Path, typer.Argument(exists=True)],
    course: Annotated[str, typer.Option("--course", help="Course id")],
    source_type: Annotated[SourceType, typer.Option("--source-type")],
    title: Annotated[str | None, typer.Option("--title")] = None,
    url: Annotated[str | None, typer.Option("--url")] = None,
    tentative: Annotated[bool, typer.Option("--tentative")] = False,
    allow_bare_dates: Annotated[
        bool,
        typer.Option(
            "--allow-bare-dates",
            help="Also match year-less M/D dates (e.g. '8/17') using the course's "
            "reference year. Only use for sources you know are a dated grid/calendar "
            "for this course -- bare M/D is ambiguous in general prose.",
        ),
    ] = False,
) -> None:
    """Parse + extract one downloaded file (syllabus PDF, D2L page dump, etc.)
    into candidate academic items, and store them.

    Computes a plan (CREATE/UPDATE/UNCHANGED/...) against whatever was
    already stored under the same fingerprints *before* writing the new
    extraction, so a revised source correctly produces UPDATEs rather than
    silently overwriting history.
    """
    with session_scope() as session:
        resolved_course_id = repository.resolve_course_id(session, course)
        if resolved_course_id is None:
            console.print(f"[red]No such course id: {course}[/red]")
            raise typer.Exit(1)
        course = resolved_course_id
        course_obj = repository.get_course(session, course)
        if course_obj is None:
            console.print(f"[red]No such course id: {course}[/red]")
            raise typer.Exit(1)

        document = _load_document(path, title or path.name)
        content_hash = document.content_hash
        # Combines the raw parser version with the extraction pipeline
        # version so a code fix to either one invalidates the dedup check --
        # otherwise re-running `extract` on unchanged content after a
        # pipeline bug fix would silently keep the old (wrong) extraction.
        processing_version = f"{document.parser_version}+{EXTRACTION_VERSION}"

        existing_source = repository.find_source_by_hash(session, course, content_hash)
        if existing_source is not None and existing_source.parser_version == processing_version:
            console.print(
                f"[yellow]Identical content already ingested and processed with the current "
                f"pipeline version as source {existing_source.id[:8]} "
                f"({existing_source.retrieved_at}). Skipping re-extraction.[/yellow]"
            )
            return
        if existing_source is not None:
            console.print(
                f"[yellow]Content unchanged since source {existing_source.id[:8]}, but the "
                "extraction pipeline has changed since then -- reprocessing.[/yellow]"
            )

        source = Source(
            id=uuid.uuid4().hex,
            course_id=course,
            source_type=source_type,
            title=title or path.name,
            url=url,
            local_path=str(path),
            retrieved_at=datetime.now(UTC),
            content_hash=content_hash,
            parser_version=processing_version,
            extracted_at=datetime.now(UTC),
            is_tentative=tentative,
        )
        source_row = repository.add_source(session, source, raw_text=document.text)

        config = get_config()
        reference_year = (
            course_obj.start_date.year if course_obj.start_date else datetime.now().year
        )
        stored_default_due = repository.get_preference(
            session, "default_due_time", default=config.deadlines.default_due_time
        )
        default_due_time = _parse_time(str(stored_default_due))
        ctx = ExtractionContext(
            course_id=course,
            source_id=source_row.id,
            reference_year=reference_year,
            term_start=course_obj.start_date,
            term_end=course_obj.end_date,
            default_due_time=default_due_time,
            reference_phrases=config.completeness.reference_phrases,
            is_tentative=tentative,
            allow_bare_dates=allow_bare_dates,
        )
        result = extract_from_document(document, ctx)

        plan = compute_plan(session, course, result.items)
        console.print(format_plan_summary(course, plan.entries))

        for item in result.items:
            repository.upsert_academic_item(session, item)
        for ref in result.unresolved:
            repository.add_unresolved_reference(session, ref)

        repository.log_audit_event(
            session,
            event_type="source_extracted",
            course_id=course,
            source_id=source_row.id,
            summary=f"Extracted {len(result.items)} item(s), "
            f"{len(result.unresolved)} unresolved reference(s) from {source.title}",
            details={"item_count": len(result.items), "unresolved_count": len(result.unresolved)},
        )

    console.print(
        f"[green]Done.[/green] {len(result.items)} candidate item(s), "
        f"{len(result.unresolved)} unresolved reference(s)."
    )


def _parse_time(value: str):
    from datetime import time

    hh, mm = value.split(":")
    return time(int(hh), int(mm))


# --------------------------------------------------------------------------
# completeness / unresolved / plan / audit / status
# --------------------------------------------------------------------------

def _resolve_course_or_exit(session, course_id: str) -> Course:
    """Accept either a full course id or the truncated 8-char prefix shown
    by `academic-sync courses`. Exits with a clear error instead of letting
    callers silently filter on an id that matches nothing."""
    resolved = repository.resolve_course_id(session, course_id)
    course = repository.get_course(session, resolved) if resolved else None
    if course is None:
        console.print(
            f"[red]No course found matching '{course_id}'.[/red] "
            "Run `academic-sync courses` to see valid ids."
        )
        raise typer.Exit(code=1)
    return course


@app.command("completeness")
def completeness_cmd(course: Annotated[str | None, typer.Option("--course")] = None) -> None:
    with session_scope() as session:
        courses = [_resolve_course_or_exit(session, course)] if course else repository.list_courses(session)
        for c in courses:
            sources = repository.list_sources_for_course(session, c.id)
            items = repository.list_items_for_course(session, c.id)
            unresolved = repository.list_unresolved_references(session, c.id)
            # A course "has modules" once any item was actually given a
            # module_label -- proof that per-chapter/per-module content
            # pages exist and are reachable in D2L, not just that they
            # might. Only then does a dated item lacking one count as a
            # gap (see CLAUDE.md invariant 17 / d2l_discovery.md#required-finds).
            course_has_modules = any(i.module_label for i in items)
            synced_or_clear = {ItemStatus.CLEAR, ItemStatus.SYNCED}
            unnested_item_count = (
                sum(
                    1 for i in items
                    if i.date is not None and i.status in synced_or_clear and not i.module_label
                )
                if course_has_modules else 0
            )
            # CLAUDE.md invariant 17 (amended): reference_url (the
            # submission/turn-in link) and resource_url (supplementary
            # material, e.g. a printout) are independently required where
            # applicable, not either/or -- an item with only a resource_url
            # still hasn't had its actual turn-in location captured.
            unlinked_item_count = sum(
                1 for i in items
                if i.date is not None and i.status in synced_or_clear
                and (i.item_type.is_deadline or i.item_type in (ItemType.EXAM, ItemType.FINAL_EXAM))
                and not i.reference_url
            )
            # CLAUDE.md invariant 26: every chapter/unit this course's
            # weekly reading blocks reference must have a saved
            # ChapterTopic row -- collect the referenced labels from every
            # WEEKLY_READING item's title (same "Chapter N: Topic; ..."
            # shape chapter_topics.split_chapter_segments already parses),
            # subtract what's actually been saved.
            known_chapter_labels = {
                canonicalize_chapter_label(label)
                for i in items if i.item_type == ItemType.WEEKLY_READING
                for label, _text in split_chapter_segments(i.title)
                if label is not None
            }
            saved_chapter_topics = repository.list_chapter_topics_for_course(session, c.id)
            saved_chapter_labels = {
                canonicalize_chapter_label(t.chapter_label) for t in saved_chapter_topics
            }
            missing_chapter_topic_count = len(known_chapter_labels - saved_chapter_labels)
            # CLAUDE.md invariant 26: a saved row isn't enough on its own --
            # it also has to be confirmed exhaustive (real complete/stable
            # structure, not a sample or an adaptive "what's next" view).
            # A row the course doesn't actually reference doesn't count
            # against it either way.
            partial_chapter_topic_count = sum(
                1 for t in saved_chapter_topics
                if canonicalize_chapter_label(t.chapter_label) in known_chapter_labels
                and not t.is_exhaustive
            )
            report = completeness_mod.analyze_completeness(
                c.id,
                inspected_source_types={s.source_type for s in sources},
                unresolved_references=unresolved,
                conflicting_date_count=sum(1 for i in items if i.status == ItemStatus.CONFLICTED),
                undated_graded_work_count=sum(
                    1 for i in items if i.status == ItemStatus.UNRESOLVED and i.item_type.is_deadline
                ),
                unnested_item_count=unnested_item_count,
                unlinked_item_count=unlinked_item_count,
                missing_chapter_topic_count=missing_chapter_topic_count,
                partial_chapter_topic_count=partial_chapter_topic_count,
                is_synthetic=c.is_synthetic,
            )
            console.print(f"\n[bold]{c.course_code} {c.section or ''} -- {c.name}[/bold]")
            console.print(format_completeness_report(report))


@app.command("unresolved")
def unresolved_cmd(
    course: Annotated[str | None, typer.Option("--course")] = None,
    show_all: Annotated[bool, typer.Option("--all")] = False,
) -> None:
    with session_scope() as session:
        resolved_course_id = _resolve_course_or_exit(session, course).id if course else None
        refs = repository.list_unresolved_references(session, course_id=resolved_course_id)
    limit = len(refs) if show_all else 20
    console.print(format_unresolved(refs, limit=limit))


@app.command("unresolved-add")
def unresolved_add_cmd(
    course: Annotated[str, typer.Option("--course")],
    description: Annotated[str, typer.Option("--description")],
    kind: Annotated[
        str,
        typer.Option(
            "--kind",
            help=f"One of: {', '.join(k.value for k in UnresolvedReferenceKind)}. "
            "Use external_reference_uninspected for a shell link off the LMS's own "
            "domain that hasn't been opened/verified yet -- see "
            "docs/d2l_discovery.md's external-courseware section.",
        ),
    ] = UnresolvedReferenceKind.EXTERNAL_REFERENCE_UNINSPECTED.value,
    source_wording: Annotated[str | None, typer.Option("--source-wording")] = None,
) -> None:
    """Record a live discovery finding that isn't something the deterministic
    `extract` pipeline can see on its own -- most commonly: "this course's
    shell has a link/nav item leaving the LMS's own domain, and the
    surrounding text/context says real assignment content is behind it, but
    it hasn't been opened and crawled yet." Recognizing that link is a live
    judgment call made while browsing (a name list of known platforms would
    just recreate the same blind spot for the next unlisted one -- see
    CLAUDE.md); this command is how that judgment call gets turned into
    something `completeness` can actually gate on, instead of depending on
    a session remembering to mention it. Cleared automatically once a
    Source is later added whose title matches --source-wording (see
    db.repository.add_source), or manually via `unresolved-resolve`.
    """
    try:
        kind_enum = UnresolvedReferenceKind(kind)
    except ValueError:
        console.print(f"[red]Unknown kind: {kind}[/red]")
        raise typer.Exit(1) from None
    with session_scope() as session:
        resolved_course_id = _resolve_course_or_exit(session, course).id
        ref = UnresolvedReference(
            id=uuid.uuid4().hex,
            course_id=resolved_course_id,
            kind=kind_enum,
            description=description,
            source_wording=source_wording,
        )
        repository.add_unresolved_reference(session, ref)
        console.print(f"[green]Recorded[/green] unresolved reference {ref.id} for {course}.")


@app.command("unresolved-resolve")
def unresolved_resolve_cmd(
    reference_id: Annotated[str, typer.Argument()],
    note: Annotated[str, typer.Option("--note")],
) -> None:
    """Mark one unresolved reference resolved, with a note explaining what
    was actually found -- use after live discovery opens a flagged link and
    determines what it is (a real courseware source worth crawling, or just
    a supplementary/marketing page that doesn't need tracking). See
    `unresolved-add`."""
    with session_scope() as session:
        ok = repository.resolve_unresolved_reference(session, reference_id, note)
    if not ok:
        console.print(f"[red]No open unresolved reference with id {reference_id}.[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Resolved[/green] {reference_id}: {note}")


_WEEKLY_LINKS_HELP = (
    'JSON array of this item\'s real resource links, e.g. '
    '\'[{"label": "Lecture Slides - Ch 23", "url": "https://..."}, '
    '{"label": "Handout: Hardy-Weinberg Practice", "url": "https://..."}, '
    '{"label": "Textbook - Ch 23", "url": "https://..."}]\'. Add whatever '
    "discovery actually found -- for a weekly banner: that week's video / "
    "slide deck / textbook reading; for a lecture: that session's own "
    "slides / handout / in-class activity / professor recording / "
    "textbook chapter -- and omit what it didn't. NEVER a syllabus link "
    "(see CLAUDE.md invariant 25). Replaces reference_url/resource_url on "
    "the LINKS line when given. WEEKLY_READING and lecture/lab meeting "
    "items only (deadline-type items keep the two fixed URL slots)."
)


def _parse_weekly_links(raw: str | None) -> list[WeeklyLink]:
    """Parse a `--links` JSON-array string into WeeklyLink objects, exiting
    with a clear message on malformed input -- same error-handling shape
    as `render --details-blocks`."""
    if raw is None:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        console.print(f"[red]--links is not valid JSON: {exc}[/red]")
        raise typer.Exit(1) from None
    if not isinstance(parsed, list):
        console.print("[red]--links must be a JSON array of {label, url} objects.[/red]")
        raise typer.Exit(1)
    try:
        return [WeeklyLink(**obj) for obj in parsed]
    except TypeError as exc:
        console.print(f"[red]--links: {exc}[/red]")
        raise typer.Exit(1) from None


@app.command("weekly-reading-add")
def weekly_reading_add_cmd(
    course: Annotated[str, typer.Option("--course")],
    week_start: Annotated[
        str, typer.Option("--week-start", help="YYYY-MM-DD, the first day of the reading week.")
    ],
    week_end: Annotated[
        str,
        typer.Option(
            "--week-end", help="YYYY-MM-DD, the last day of the reading week (inclusive)."
        ),
    ],
    chapters: Annotated[
        str,
        typer.Option(
            "--chapters",
            help='The week\'s chapter/topic content, e.g. "Chapter 12: Cellular '
            'Respiration; Chapter 13: Photosynthesis" -- the same "Chapter N: Topic" '
            "shape a multi-chapter lecture title already uses, semicolon-separated. "
            "Must trace to real instructor material (module page, syllabus topic "
            "table, etc.) -- never a generated paraphrase, see CLAUDE.md invariant 22. "
            "For a --synthetic course, this is instead a short, AI-authored topic/pacing "
            "label -- see CLAUDE.md invariant 35.",
        ),
    ],
    reference_url: Annotated[str | None, typer.Option("--reference-url")] = None,
    reference_url_label: Annotated[str | None, typer.Option("--reference-url-label")] = None,
    resource_url: Annotated[str | None, typer.Option("--resource-url")] = None,
    resource_url_label: Annotated[str | None, typer.Option("--resource-url-label")] = None,
    links: Annotated[str | None, typer.Option("--links", help=_WEEKLY_LINKS_HELP)] = None,
) -> None:
    """Create or refresh a course's weekly reading block -- one all-day event
    spanning [--week-start, --week-end] that's a heads-up of everything that
    class will cover that week (see CLAUDE.md invariant 25 and
    docs/d2l_discovery.md's weekly-reading section). This replaces the old
    per-day standalone READING event entirely -- a plain READING item can no
    longer sync as its own event (sync/calendar_payload.py raises for it).

    Week boundaries must trace to real D2L module start/stop metadata or a
    syllabus week<->topic table -- never assumed Mon-Sun. Idempotent by
    (course, week-start): re-running this for the same week updates the same
    item instead of creating a duplicate (same fingerprint mechanism as
    every other item type -- see reconciliation/fingerprint.py).

    After this, run `render <item_id> --details "..."` to get the exact
    Calendar payload -- `--details` is where any real, source-stated
    internal pacing (e.g. "Ch. 12 by Wednesday, Ch. 13 by Friday") goes,
    same never-persisted, supplied-at-render-time convention `render`
    already uses for a lecture's DETAILS; omit it entirely when the source
    doesn't differentiate timing within the week. Then
    create_event/update_event + `record-sync`, same Step 5 flow as any
    other item.
    """
    with session_scope() as session:
        resolved_course_id = _resolve_course_or_exit(session, course).id
        start = date.fromisoformat(week_start)
        end = date.fromisoformat(week_end)
        if end < start:
            console.print("[red]--week-end is before --week-start.[/red]")
            raise typer.Exit(1)
        weekly_links = _parse_weekly_links(links)

        fingerprint = compute_fingerprint(
            resolved_course_id,
            ItemType.WEEKLY_READING.value,
            "Readings",
            disambiguator=start.isoformat(),
        )
        item = AcademicItem(
            id=uuid.uuid4().hex,
            course_id=resolved_course_id,
            item_type=ItemType.WEEKLY_READING,
            title=chapters,
            date=start,
            date_range_end=end,
            status=ItemStatus.CLEAR,
            is_derived=True,
            derivation_rule="weekly_reading_aggregation",
            reference_url=reference_url,
            reference_url_label=reference_url_label,
            resource_url=resource_url,
            resource_url_label=resource_url_label,
            weekly_links=weekly_links,
            fingerprint=fingerprint,
        )

        plan = compute_plan(session, resolved_course_id, [item])
        console.print(format_plan_summary(resolved_course_id, plan.entries))

        row = repository.upsert_academic_item(session, item)
        console.print(f"[green]Saved[/green] weekly reading block {row.id} for {course}.")


@app.command("export-ics")
def export_ics_cmd(
    course: Annotated[str, typer.Option("--course")],
    out: Annotated[Path, typer.Option("--out", help="Where to write the .ics file.")],
) -> None:
    """Write every syncable item of a course to one .ics file, rendered
    through exactly the same path as `render` -- for sharing a course (e.g. a
    premade synthetic one in the study-prompt-system repo's courses/ folder)
    that anyone can import into Google Calendar. Never includes guests or
    conference links. Stable UIDs (the item fingerprint) mean re-importing an
    updated file updates events instead of duplicating them."""
    with session_scope() as session:
        resolved = _resolve_course_or_exit(session, course)
        events: list[IcsEvent] = []
        skipped = 0
        for item in repository.list_items_for_course(session, resolved.id):
            if (
                item.item_type == ItemType.READING
                or item.status == ItemStatus.SUPERSEDED
                or not item.is_ready_to_sync()
                or not item.fingerprint
            ):
                skipped += 1
                continue
            payload, _calendar_id = _render_item_payload(
                session, item, resolved, nesting=item.module_label,
            )
            events.append(IcsEvent(uid=f"{item.fingerprint}@study-prompt-system", payload=payload))
        if not events:
            console.print(f"[red]{resolved.course_code} has no syncable items to export.[/red]")
            raise typer.Exit(1)
        stamp_date = resolved.start_date or date(2000, 1, 1)
        text_out = build_ics(
            resolved.name,
            events,
            dtstamp=datetime(stamp_date.year, stamp_date.month, stamp_date.day, tzinfo=UTC),
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text_out.encode("utf-8"))
    console.print(
        f"[green]Wrote[/green] {len(events)} event(s) to {out}"
        + (f" ({skipped} unsyncable item(s) skipped)" if skipped else "")
    )


@app.command("chapter-topic-add")
def chapter_topic_add_cmd(
    course: Annotated[str, typer.Option("--course")],
    chapter: Annotated[
        str, typer.Option("--chapter", help='e.g. "Chapter 23" or "Unit 2" -- the same '
                           '"Chapter N"/"Unit N" label a weekly reading block\'s --chapters '
                           "or a lecture's multi-chapter title uses. This is the lookup key "
                           "(canonicalized) render auto-pulls from for a weekly banner's "
                           "THIS WEEK content -- see CLAUDE.md invariant 26."),
    ],
    title: Annotated[str | None, typer.Option("--title", help='e.g. "Evolution of Populations"')] = None,
    vocabulary: Annotated[
        str | None,
        typer.Option("--vocabulary", help="Comma-separated real vocabulary terms from the "
                     "course's own chapter objectives/study-guide material."),
    ] = None,
    objective: Annotated[
        list[str] | None,
        typer.Option("--objective", help="Repeatable -- one real objective per flag, e.g. "
                     '--objective "Explain X" --objective "Distinguish Y". Every value must '
                     "trace to real instructor-authored material -- never a generated "
                     "summary (CLAUDE.md invariant 22). Must be the platform's real, complete "
                     "topic/subtopic list, not a representative sample -- see CLAUDE.md "
                     "invariant 26."),
    ] = None,
    exhaustive: Annotated[
        bool,
        typer.Option("--exhaustive", help="Set only once you've actually confirmed this is the "
                     "platform's real, complete, stable topic list for this chapter -- e.g. "
                     "ALEKS's own \"View All Topics\" view, not its personalized \"Ready to "
                     "Learn\" queue. Leave unset (default False) if capture might still be "
                     "partial or was pulled from an adaptive/progress-dependent view -- "
                     "`completeness` flags unconfirmed rows separately from missing ones "
                     "(`partial_chapter_topic_count`) so they get revisited."),
    ] = False,
) -> None:
    """Save (or refresh) a course's real chapter/unit topic breakdown --
    the durable source of truth `render` auto-pulls from for a weekly
    reading block's THIS WEEK content, and (going forward) a lecture's own
    DETAILS, instead of hand-typed content that only ever lived in one
    Calendar event's description. Required during a full course scan for
    every chapter/unit the course has, not just ones near a current dated
    item -- see CLAUDE.md invariant 26 and docs/d2l_discovery.md's
    required-finds. Idempotent by (course, chapter label): re-running this
    for the same chapter updates the same row instead of duplicating."""
    with session_scope() as session:
        resolved_course_id = _resolve_course_or_exit(session, course).id
        topic = ChapterTopic(
            id=uuid.uuid4().hex,
            course_id=resolved_course_id,
            chapter_label=chapter,
            title=title,
            vocabulary=vocabulary,
            objectives=objective or [],
            is_exhaustive=exhaustive,
        )
        row = repository.upsert_chapter_topic(session, topic)
        exhaustive_note = "" if exhaustive else " [yellow](not yet confirmed exhaustive)[/yellow]"
        console.print(
            f"[green]Saved[/green] chapter topic {row.id} ({chapter}) for {course}.{exhaustive_note}"
        )


@app.command("needs-link-refresh")
def needs_link_refresh_cmd(
    course: Annotated[str | None, typer.Option("--course")] = None,
    lookback_days: Annotated[int, typer.Option("--lookback-days")] = 14,
    lookahead_days: Annotated[int, typer.Option("--lookahead-days")] = 14,
) -> None:
    """List items whose link_available_date falls within the last
    --lookback-days or the next --lookahead-days, and that still have no
    reference_url/resource_url -- i.e. discovery found them locked behind a
    release date, and that date has either already passed (worth a re-check
    now) or is coming up soon (worth checking a bit early, since D2L's
    stated date is sometimes conservative and an item can be unlocked
    before it). Meant to run weekly -- see the recurring Sunday-evening
    Calendar reminder academic-import sets up, and its Step 6 for the full
    workflow. Drives the academic-import skill's periodic "link refresh"
    pass -- see CLAUDE.md and .claude/skills/academic-import/SKILL.md.
    Prints nothing extra when the list is empty; that's the common case on
    any given week.
    """
    with session_scope() as session:
        resolved_course_id = _resolve_course_or_exit(session, course).id if course else None
        items = repository.list_items_needing_link_recheck(
            session, course_id=resolved_course_id,
            lookback_days=lookback_days, lookahead_days=lookahead_days,
        )
        if not items:
            console.print("[green]Nothing needs a link refresh right now.[/green]")
            return
        console.print(f"{len(items)} item(s) whose link is worth checking:")
        codes = {c.id: c.course_code for c in repository.list_courses(session)}
        today = date.today()
        for item in sorted(items, key=lambda i: (i.date is None, i.date)):
            course_code = codes.get(item.course_id, item.course_id)
            when = "opened" if (item.link_available_date and item.link_available_date <= today) else "opens"
            console.print(
                f"  [{course_code}] {item.title} ({item.date}) -- "
                f"{when} {item.link_available_date} -- item_id {item.id}"
            )


@app.command("plan")
def plan_cmd(
    course: Annotated[str | None, typer.Option("--course")] = None,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Show what a sync would do right now, using currently stored items.

    Superseded 2026-08-25: this used to say standalone `plan` could only
    ever report UNCHANGED for an already-synced item, since it has no
    fresh extraction to diff against. That's no longer true --
    `decide_action` now compares each item's current state against
    `SyncRecord.last_synced_fields`, a real snapshot of what was actually
    last pushed (see `reconciliation/engine.py::snapshot_compared_fields`
    and CLAUDE.md invariant 5's 2026-08-25 amendment), so drift from
    enrichment applied directly via `render --save` (module_label,
    reference_url, etc.) after an item's first sync now correctly shows as
    UPDATE even with no fresh extraction involved. A `SyncRecord` from
    before this fix has no snapshot to compare against and is reported as
    UPDATE unconditionally (a one-time backfill push, not a sign something
    is actually wrong) -- `record-sync` populates the snapshot the moment
    that push happens, after which this command's UNCHANGED becomes
    trustworthy again for that item.
    """
    with session_scope() as session:
        courses = [_resolve_course_or_exit(session, course)] if course else repository.list_courses(session)
        for c in courses:
            items = repository.list_items_for_course(session, c.id)
            plan = compute_plan(session, c.id, items)
            console.print(f"\n[bold]{c.course_code}[/bold]")
            console.print(format_plan_summary(c.id, plan.entries))
            if verbose:
                console.print(format_plan_detail(plan.entries))


@app.command("export")
def export_cmd(
    course: Annotated[str | None, typer.Option("--course")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    """Write a consolidated, human-and-agent-readable text file of every
    known item for a course (sync-ready, needs-review, undated, and open
    unresolved references) to
    data/downloads/<COURSE_CODE>/consolidated_events.txt (or --output).
    Run this after any extract pass so the course's folder always reflects
    current state -- a future session (or you) can read this one file
    instead of re-deriving from raw source documents.
    """
    with session_scope() as session:
        courses = [_resolve_course_or_exit(session, course)] if course else repository.list_courses(session)
        for c in courses:
            items = repository.list_items_for_course(session, c.id)
            unresolved = repository.list_unresolved_references(session, c.id)
            text = format_course_export(c, items, unresolved)

            out_path = output or (
                REPO_ROOT / "data" / "downloads" / c.course_code / "consolidated_events.txt"
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(text, encoding="utf-8")
            console.print(f"[green]Wrote[/green] {out_path} ({len(items)} items)")


@app.command("audit")
def audit_cmd(limit: Annotated[int, typer.Option("--limit")] = 50) -> None:
    with session_scope() as session:
        entries = repository.list_audit_log(session, limit=limit)
    for e in entries:
        console.print(f"[dim]{e.timestamp.isoformat()}[/dim] [{e.event_type}] {e.summary}")


@app.command("status")
def status_cmd() -> None:
    with session_scope() as session:
        courses = repository.list_courses(session)
        table = Table(show_header=True)
        for col in ["course", "term", "items", "unresolved", "synced"]:
            table.add_column(col)
        for c in courses:
            items = repository.list_items_for_course(session, c.id)
            unresolved = repository.list_unresolved_references(session, c.id)
            synced = sum(1 for i in items if i.status == ItemStatus.SYNCED)
            table.add_row(c.course_code, c.term, str(len(items)), str(len(unresolved)), str(synced))
        console.print(table)


@app.command("record-sync")
def record_sync_cmd(
    item_id: Annotated[str, typer.Argument()],
    event_id: Annotated[str, typer.Option("--event-id")],
    calendar_id: Annotated[str, typer.Option("--calendar-id")],
) -> None:
    """Record that the import skill actually wrote a Calendar event for this
    item. Called by the skill immediately after a successful
    create_event/update_event -- never called speculatively."""
    with session_scope() as session:
        item = repository.get_academic_item(session, item_id)
        if item is None:
            console.print(f"[red]No such item: {item_id}[/red]")
            raise typer.Exit(1)
        repository.upsert_sync_record(
            session,
            academic_item_id=item_id,
            google_calendar_id=calendar_id,
            google_event_id=event_id,
            last_synced_fields=snapshot_compared_fields(item),
            status=SyncAction.UNCHANGED,
            mark_synced=True,
        )
        item.status = ItemStatus.SYNCED
        item.calendar_event_id = event_id
        repository.upsert_academic_item(session, item)
        repository.log_audit_event(
            session, event_type="calendar_event_synced", item_id=item_id,
            summary=f"Recorded Calendar sync for {item.title}",
            details={"event_id": event_id, "calendar_id": calendar_id},
        )
    console.print("[green]Recorded.[/green]")


def _render_item_payload(
    session: Session,
    item: AcademicItem,
    course: Course,
    *,
    nesting: str | None,
    details: str | None = None,
    required_resources: str | None = None,
    location_info: LocationInfo | None = None,
) -> tuple[dict[str, Any], str]:
    """The one render path shared by `render` and `export-ics`: picks the
    right description builder for the item, then builds the full Calendar
    payload. Returns (payload, target calendar id)."""
    config = get_config()
    color_id = str(
        repository.get_preference(session, "calendar_color_id", default=config.calendar.color_id)
    )
    calendar_id = str(
        repository.get_preference(
            session, "target_calendar_id", default=config.calendar.target_calendar_id
        )
    )
    timezone = str(repository.get_preference(session, "timezone", default=config.timezone))
    is_physical_meeting = item.item_type.is_fixed_time_meeting and item.due_time is None

    primary_source = (
        repository.get_source(session, item.source_ids[0]) if item.source_ids else None
    )
    platform_label = platform_label_for_source(primary_source)

    if item.item_type == ItemType.WEEKLY_READING:
        # Auto-pull saved chapter topics (CLAUDE.md invariant 26) --
        # THIS WEEK becomes the real vocabulary/objectives breakdown
        # for any chapter that's been captured via `chapter-topic-add`,
        # instead of the bare chapter-list line. Only switches to the
        # richer rendering once at least one real chapter topic is
        # found; with none found, this_week stays None and
        # build_weekly_reading_description falls back to its original
        # bare _topic_line(item.title) behavior unchanged.
        segments = split_chapter_segments(item.title) if item.title else []
        topics_by_label: dict[str, ChapterTopic] = {}
        for label, _text in segments:
            if label is None:
                continue
            topic = repository.get_chapter_topic(session, item.course_id, label)
            if topic is not None:
                topics_by_label[canonicalize_chapter_label(label)] = topic
        this_week = None
        if topics_by_label:
            block_dicts = build_chapter_topic_blocks(segments, topics_by_label)
            this_week = format_details_blocks([DetailsBlock(**b) for b in block_dicts])
        description = build_weekly_reading_description(
            item, course, this_week=this_week, pacing=details,
        )
    elif is_physical_meeting:
        description = build_meeting_description(
            item, course, location=location_info, nesting=nesting, details=details,
            platform_label=platform_label,
        )
    else:
        description = build_deadline_description(
            item, course, nesting=nesting, details=details, required_resources=required_resources,
            platform_label=platform_label,
        )

    payload = build_event_payload(
        item, course, timezone=timezone, color_id=color_id,
        description=description, location=location_info,
    )
    return payload, calendar_id


@app.command("render")
def render_cmd(
    item_id: Annotated[str, typer.Argument()],
    reference_url: Annotated[str | None, typer.Option("--reference-url")] = None,
    reference_url_label: Annotated[str | None, typer.Option("--reference-url-label")] = None,
    resource_url: Annotated[str | None, typer.Option("--resource-url")] = None,
    resource_url_label: Annotated[str | None, typer.Option("--resource-url-label")] = None,
    links: Annotated[str | None, typer.Option("--links", help=_WEEKLY_LINKS_HELP)] = None,
    link_available_date: Annotated[
        str | None,
        typer.Option("--link-available-date", help="YYYY-MM-DD -- only when D2L showed an "
                     "explicit 'Available on' date for a still-locked item; see the "
                     "academic-import SKILL.md link-refresh step."),
    ] = None,
    points: Annotated[float | None, typer.Option("--points")] = None,
    optional: Annotated[bool, typer.Option("--optional")] = False,
    inferred_date: Annotated[
        bool,
        typer.Option(
            "--inferred-date",
            help="Mark this item's date as pattern-inferred rather than literally "
            "sourced -- only after exhaustive real search found nothing, per a "
            "stated one-sentence rule (see --date-inference-rule). Renders a "
            "visible '(Inferred Date)' tag. See CLAUDE.md invariant 29.",
        ),
    ] = False,
    date_inference_rule: Annotated[
        str | None,
        typer.Option(
            "--date-inference-rule",
            help="The one-sentence auditable pattern rule that justified "
            "--inferred-date (e.g. 'every other HW this course is due exactly "
            "N days after the prior chapter exam'). Stored for local audit only "
            "-- never rendered into the visible description.",
        ),
    ] = None,
    details: Annotated[str | None, typer.Option("--details")] = None,
    details_blocks: Annotated[
        str | None,
        typer.Option(
            "--details-blocks",
            help='JSON array of labeled sub-groups for DETAILS, e.g. '
            '\'[{"label": "Vocabulary", "text": "..."}, {"label": "Objectives", '
            '"items": ["...", "..."]}]\' -- renders labeled sub-groups with one '
            "bullet line per items entry instead of a single run-on paragraph. "
            "Takes precedence over --details when both are given. Use this "
            "whenever DETAILS has real vocabulary/objectives/multi-point "
            "structure; plain --details is still fine for a single short "
            "paragraph. Every item/text value must still trace to real source "
            "content -- see CLAUDE.md invariant 22.",
        ),
    ] = None,
    nesting: Annotated[str | None, typer.Option("--nesting")] = None,
    required_resources: Annotated[str | None, typer.Option("--required-resources")] = None,
    location: Annotated[
        str | None,
        typer.Option("--location", help="Pre-resolved location string (room/Online/etc) -- "
                     "this command doesn't resolve location preferences itself."),
    ] = None,
    save: Annotated[
        bool,
        typer.Option("--save", help="Persist the --reference-url/--points/etc. overrides "
                     "onto the item row, not just use them for this render."),
    ] = False,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Print the computed payload as one JSON object "
                     "(summary/description/location/allDay/startTime/endTime/timeZone/"
                     "colorId/calendarId/itemId) instead of the human-readable field "
                     "dump -- for scripted batch rendering ahead of many live "
                     "create_event/update_event calls (see academic-import SKILL.md "
                     "Step 5). Same computed values either way; this only changes "
                     "output formatting."),
    ] = False,
) -> None:
    """Compute the EXACT summary/description/location/start/end this item
    would sync with, using the same build_title/build_*_description/
    build_event_payload functions CLAUDE.md and docs/d2l_discovery.md
    document as the single source of truth for that format.

    Run this before every live create_event/update_event call during Step 5
    of the academic-import skill and copy its output directly into the tool
    call -- don't hand-type the HTML template from memory of the prose
    rules. That's exactly the kind of mechanical step where a fresh session
    (or this one, hours in) can silently drift from the documented format
    (wrong separator, missing <br>, mislabeled link) without ever running
    afoul of the "never fabricate" invariants -- this command removes that
    risk by making the tested code the thing that actually produces the
    text, not a description of it.

    Use --details-blocks instead of plain --details whenever DETAILS has
    real vocabulary/objectives/multi-point structure -- it renders labeled
    sub-groups with one bullet line per point instead of a hand-typed
    run-on paragraph, and (like --details) is never persisted, always
    supplied fresh at render time.

    --reference-url/--resource-url/--points/--optional/etc. let you supply
    metadata gathered during discovery that isn't on the item row yet
    (extraction doesn't currently detect these automatically -- see
    docs/d2l_discovery.md#links and #points-and-optionalextra-credit).
    Pass --save to persist them for next time; without it, this is a
    pure preview and the item row is untouched.
    """
    with session_scope() as session:
        item = repository.get_academic_item(session, item_id)
        if item is None:
            console.print(f"[red]No such item: {item_id}[/red]")
            raise typer.Exit(1)
        if item.date is None:
            console.print(f"[red]Item {item_id} has no date -- cannot render a Calendar payload.[/red]")
            raise typer.Exit(1)
        if item.item_type == ItemType.WEEKLY_READING and item.date_range_end is None:
            console.print(
                f"[red]Item {item_id} is a weekly reading block with no date_range_end -- "
                "cannot render a Calendar payload.[/red]"
            )
            raise typer.Exit(1)
        if item.item_type == ItemType.READING:
            console.print(
                f"[red]Item {item_id} is a plain READING item -- these never sync as their own "
                "event. Fold its content into the covering lecture's DETAILS or the course's "
                "weekly reading block instead (see CLAUDE.md invariant 25).[/red]"
            )
            raise typer.Exit(1)
        course = repository.get_course(session, item.course_id)
        if course is None:
            console.print(f"[red]Item {item_id} references a missing course.[/red]")
            raise typer.Exit(1)

        if reference_url is not None:
            item.reference_url = reference_url
        if reference_url_label is not None:
            item.reference_url_label = reference_url_label
        if resource_url is not None:
            item.resource_url = resource_url
        if resource_url_label is not None:
            item.resource_url_label = resource_url_label
        if links is not None:
            if item.item_type == ItemType.WEEKLY_READING or item.item_type.is_routine_meeting:
                item.weekly_links = _parse_weekly_links(links)
            else:
                console.print(
                    f"[yellow]Ignoring --links for item {item_id}[/yellow]: only "
                    "WEEKLY_READING banners and lecture/lab meetings use the "
                    "multi-link list; deadline-type items use "
                    "--reference-url/--resource-url."
                )
        if link_available_date is not None:
            item.link_available_date = date.fromisoformat(link_available_date)
        if points is not None:
            item.points = points
        if optional:
            item.is_optional = True
        if inferred_date:
            if not date_inference_rule:
                console.print(
                    "[red]--inferred-date requires --date-inference-rule (the "
                    "one-sentence auditable rule) -- see CLAUDE.md invariant 29.[/red]"
                )
                raise typer.Exit(1)
            item.is_inferred_date = True
            item.date_inference_rule = date_inference_rule

        # `item.module_label` is the persisted nesting field -- an explicit
        # --nesting overrides it (and is written back so it isn't lost
        # next render), but absent that, module_label is the real source
        # of truth. Previously --nesting was render-time-only and
        # module_label was silently ignored unless --nesting happened to
        # be re-typed identically every time -- see CLAUDE.md invariant 17.
        if nesting is not None:
            item.module_label = nesting
        else:
            nesting = item.module_label

        if save:
            repository.upsert_academic_item(session, item)

        is_physical_meeting = item.item_type.is_fixed_time_meeting and item.due_time is None
        if location and not is_physical_meeting:
            console.print(
                f"[yellow]Ignoring --location for item {item_id}[/yellow]: "
                f"{item.item_type.value} items aren't a physical meeting -- "
                "location is reserved for lecture/lab/exam-with-a-room. Put "
                "where the work actually happens in --nesting instead "
                "(e.g. \"ALEKS\" or \"D2L\")."
            )
            location = None
        location_info = LocationInfo(platform_location=location) if location else None

        if details_blocks is not None:
            try:
                raw_blocks = json.loads(details_blocks)
            except json.JSONDecodeError as exc:
                console.print(f"[red]--details-blocks is not valid JSON: {exc}[/red]")
                raise typer.Exit(1) from None
            if not isinstance(raw_blocks, list):
                console.print("[red]--details-blocks must be a JSON array of objects.[/red]")
                raise typer.Exit(1)
            try:
                blocks = [DetailsBlock(**b) for b in raw_blocks]
            except TypeError as exc:
                console.print(f"[red]--details-blocks: {exc}[/red]")
                raise typer.Exit(1) from None
            details = format_details_blocks(blocks)

        payload, calendar_id = _render_item_payload(
            session, item, course, nesting=nesting, details=details,
            required_resources=required_resources, location_info=location_info,
        )

    # The description contains literal "[academic-sync:fp:...]" text (the
    # idempotency tag) -- Rich's console.print interprets square brackets as
    # its own markup syntax by default and will silently mangle/strip that
    # tag unless every dynamic value is escaped. This command's whole point
    # is "copy this output verbatim," so getting this wrong would be worse
    # than not having the command at all -- always escape(), never
    # interpolate a payload value into console.print raw.
    if as_json:
        is_all_day = "date" in payload["start"]
        out = {
            "itemId": item.id,
            "summary": payload["summary"],
            "description": payload["description"],
            "location": payload.get("location"),
            "allDay": is_all_day,
            "startTime": payload["start"]["date"] if is_all_day else payload["start"]["dateTime"],
            "endTime": payload["end"]["date"] if is_all_day else payload["end"]["dateTime"],
            "timeZone": None if is_all_day else payload["start"]["timeZone"],
            "colorId": payload["colorId"],
            "calendarId": calendar_id,
        }
        print(json.dumps(out))
        return

    def _field(label: str, value: str) -> None:
        console.print(f"[bold]{label}[/bold]\n{escape(value)}\n")

    _field("summary", payload["summary"])
    _field("description", payload["description"])
    _field("location", str(payload.get("location", "(none)")))
    if "date" in payload["start"]:
        _field("allDay", "true")
        _field("startTime", payload["start"]["date"])
        _field("endTime", payload["end"]["date"])
    else:
        _field("allDay", "false")
        _field("startTime", payload["start"]["dateTime"])
        _field("endTime", payload["end"]["dateTime"])
        _field("timeZone", payload["start"]["timeZone"])
    _field("colorId", payload["colorId"])
    _field("calendarId (target_calendar_id preference)", calendar_id)


# --------------------------------------------------------------------------
# grade diagnostics
# --------------------------------------------------------------------------

_DIAGNOSTIC_COLOR_PREF_KEYS = {
    DiagnosticStatus.RED: "diagnostic_color_red",
    DiagnosticStatus.YELLOW: "diagnostic_color_yellow",
    DiagnosticStatus.GREEN: "diagnostic_color_green",
}

_MAJOR_ASSESSMENT_TYPES = {ItemType.EXAM, ItemType.FINAL_EXAM, ItemType.PROJECT}


@app.command("grade-snapshot-add")
def grade_snapshot_add_cmd(
    course: Annotated[str, typer.Option("--course")],
    title: Annotated[str, typer.Option("--title")],
    week_start: Annotated[
        str, typer.Option("--week-start", help="YYYY-MM-DD, the Monday of the diagnosed week.")
    ],
    item_id: Annotated[
        str | None,
        typer.Option("--item-id", help="The matching AcademicItem id, if the gradebook row "
                     "maps cleanly to one. Leave unset rather than guessing."),
    ] = None,
    score_percent: Annotated[float | None, typer.Option("--score-percent")] = None,
    missing: Annotated[bool, typer.Option("--missing")] = False,
    feedback: Annotated[
        str | None,
        typer.Option("--feedback", help="Literal instructor feedback text, if D2L/ALEKS showed "
                     "any -- never invented. Omit if there's no real feedback."),
    ] = None,
    source_type: Annotated[str, typer.Option("--source-type")] = SourceType.D2L_QUIZZES.value,
) -> None:
    """Record one graded/missing item observed during a weekly
    grade-diagnostic crawl (see
    docs/d2l_discovery.md#weekly-grade-diagnostic-crawl). Idempotent by
    (course, title, week-start): re-running this for the same item/week
    updates the same snapshot instead of duplicating."""
    with session_scope() as session:
        resolved_course_id = _resolve_course_or_exit(session, course).id
        snapshot = GradeSnapshot(
            id=uuid.uuid4().hex,
            course_id=resolved_course_id,
            academic_item_id=item_id,
            title=title,
            week_start=date.fromisoformat(week_start),
            captured_at=datetime.now(UTC).date(),
            score_percent=score_percent,
            is_missing=missing,
            instructor_feedback=feedback,
            source_type=SourceType(source_type),
        )
        row = repository.add_grade_snapshot(session, snapshot)
        console.print(f"[green]Saved[/green] grade snapshot {row.id} ({title}) for {course}.")


@app.command("course-grade-snapshot-add")
def course_grade_snapshot_add_cmd(
    course: Annotated[str, typer.Option("--course")],
    week_start: Annotated[str, typer.Option("--week-start")],
    overall_percent: Annotated[float | None, typer.Option("--overall-percent")] = None,
    letter_grade: Annotated[str | None, typer.Option("--letter-grade")] = None,
) -> None:
    """Record a course's overall grade as of a diagnosed week -- the
    week-over-week comparison basis for `diagnostic-compute`. Idempotent by
    (course, week-start)."""
    with session_scope() as session:
        resolved_course_id = _resolve_course_or_exit(session, course).id
        snapshot = CourseGradeSnapshot(
            id=uuid.uuid4().hex,
            course_id=resolved_course_id,
            week_start=date.fromisoformat(week_start),
            captured_at=datetime.now(UTC).date(),
            overall_percent=overall_percent,
            letter_grade=letter_grade,
        )
        row = repository.add_course_grade_snapshot(session, snapshot)
        console.print(f"[green]Saved[/green] course grade snapshot {row.id} for {course}.")


@app.command("diagnostic-compute")
def diagnostic_compute_cmd(
    week_start: Annotated[str, typer.Option("--week-start")],
) -> None:
    """Classify every active, real (non-synthetic) course's Red/Yellow/Green
    status for the given diagnosed week -- read-only, writes nothing. Run
    this after recording every course's snapshots for the week, before
    building each course's own event with `diagnostic-render` -- each
    course gets its own "<CODE> Previous Week Diagnostic" event now
    (user-directed 2026-09-17), so there is no single cross-course
    status/fingerprint at this step."""
    week_start_date = date.fromisoformat(week_start)
    with session_scope() as session:
        courses = [c for c in repository.list_courses(session) if not c.is_synthetic]
        table = Table(show_header=True)
        for col in ["course", "status", "previous %", "current %", "missing", "existing event"]:
            table.add_column(col)
        for c in courses:
            current = repository.get_course_grade_snapshot(session, c.id, week_start_date)
            previous = repository.get_previous_course_grade_snapshot(
                session, c.id, before=week_start_date
            )
            item_snapshots = repository.list_grade_snapshots_for_week(session, c.id, week_start_date)
            items = repository.list_items_for_course(session, c.id)
            major_ids = frozenset(i.id for i in items if i.item_type in _MAJOR_ASSESSMENT_TYPES)
            status = diagnostics_mod.classify_course(
                current=current, previous=previous, item_snapshots=item_snapshots,
                major_assessment_item_ids=major_ids,
            )
            missing_count = sum(1 for s in item_snapshots if s.is_missing)
            existing = repository.get_weekly_diagnostic_record(session, c.id, week_start_date)
            table.add_row(
                c.course_code,
                status.value,
                f"{previous.overall_percent:g}%"
                if previous and previous.overall_percent is not None else "-",
                f"{current.overall_percent:g}%"
                if current and current.overall_percent is not None else "-",
                str(missing_count),
                existing.google_event_id if existing and existing.google_event_id else "none (CREATE)",
            )
    console.print(table)


@app.command("diagnostic-render")
def diagnostic_render_cmd(
    course: Annotated[str, typer.Option("--course")],
    week_start: Annotated[str, typer.Option("--week-start")],
    section: Annotated[
        str,
        typer.Option("--section", help="JSON object for this course's diagnostic section -- see "
                     "academic-sync SKILL.md Step 3.4 for the exact shape (course_code, status, "
                     "previous_grade_label, current_grade_label, assignments[], announcements[], "
                     "missed_deadlines[], upcoming_deadlines[], plan[])."),
    ],
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Build the exact title/description/start/end/colorId for one course's
    own "<CODE> Previous Week Diagnostic" event -- don't hand-type the HTML
    template, same reasoning as `render` for a normal item. One event per
    course, each independently colored Red/Yellow/Green (user-directed
    2026-09-17). Prints the fingerprint and any existing google_event_id so
    the caller knows CREATE vs. UPDATE."""
    week_start_date = date.fromisoformat(week_start)
    try:
        raw_section = json.loads(section)
    except json.JSONDecodeError as exc:
        console.print(f"[red]--section is not valid JSON: {exc}[/red]")
        raise typer.Exit(1) from None
    if not isinstance(raw_section, dict):
        console.print("[red]--section must be a JSON object.[/red]")
        raise typer.Exit(1)
    try:
        course_section = DiagnosticCourseSection(
            course_code=raw_section["course_code"],
            status=DiagnosticStatus(raw_section["status"]),
            previous_grade_label=raw_section.get("previous_grade_label"),
            current_grade_label=raw_section.get("current_grade_label"),
            assignments=[DiagnosticAssignment(**a) for a in raw_section.get("assignments", [])],
            announcements=raw_section.get("announcements", []),
            missed_deadlines=raw_section.get("missed_deadlines", []),
            upcoming_deadlines=raw_section.get("upcoming_deadlines", []),
            plan=raw_section.get("plan", []),
        )
    except (TypeError, KeyError, ValueError) as exc:
        console.print(f"[red]--section: {exc}[/red]")
        raise typer.Exit(1) from None

    description = build_weekly_diagnostic_description(course_section)
    with session_scope() as session:
        resolved_course = _resolve_course_or_exit(session, course)
        fingerprint = compute_fingerprint(
            resolved_course.id, "weekly_diagnostic", "Previous Week Diagnostic",
            disambiguator=week_start_date.isoformat(),
        )
        existing = repository.get_weekly_diagnostic_record(
            session, resolved_course.id, week_start_date
        )
        color_key = _DIAGNOSTIC_COLOR_PREF_KEYS[course_section.status]
        color_id = str(prefs_mod.get_pref(session, color_key))
    record_id = existing.id if existing else uuid.uuid4().hex
    payload = build_weekly_diagnostic_payload(
        course_section.course_code, week_start_date, description, fingerprint=fingerprint,
        record_id=record_id, color_id=color_id,
    )

    if as_json:
        print(json.dumps({
            "recordId": record_id,
            "courseId": resolved_course.id,
            "summary": payload["summary"],
            "description": payload["description"],
            "startTime": payload["start"]["date"],
            "endTime": payload["end"]["date"],
            "colorId": payload["colorId"],
            "status": course_section.status.value,
            "fingerprint": fingerprint,
            "existingEventId": existing.google_event_id if existing else None,
        }))
        return

    def _field(label: str, value: str) -> None:
        console.print(f"[bold]{label}[/bold]\n{escape(value)}\n")

    _field("status", course_section.status.value)
    _field("summary", payload["summary"])
    _field("description", payload["description"])
    _field("allDay", "true")
    _field("startTime", payload["start"]["date"])
    _field("endTime", payload["end"]["date"])
    _field("colorId", payload["colorId"])
    _field(
        "existingEventId (update this instead of creating, if set)",
        existing.google_event_id if existing and existing.google_event_id else "(none -- CREATE)",
    )


@app.command("diagnostic-record-sync")
def diagnostic_record_sync_cmd(
    course: Annotated[str, typer.Option("--course")],
    week_start: Annotated[str, typer.Option("--week-start")],
    event_id: Annotated[str, typer.Option("--event-id")],
    status: Annotated[str, typer.Option("--status")],
    calendar_id: Annotated[str | None, typer.Option("--calendar-id")] = None,
) -> None:
    """Record that the skill actually wrote this course's own "<CODE>
    Previous Week Diagnostic" Calendar event for this week -- called
    immediately after a successful create_event/update_event, mirrors
    `record-sync` for a normal item."""
    week_start_date = date.fromisoformat(week_start)
    with session_scope() as session:
        resolved_course_id = _resolve_course_or_exit(session, course).id
        fingerprint = compute_fingerprint(
            resolved_course_id, "weekly_diagnostic", "Previous Week Diagnostic",
            disambiguator=week_start_date.isoformat(),
        )
        repository.upsert_weekly_diagnostic_record(
            session, course_id=resolved_course_id, week_start=week_start_date,
            status=DiagnosticStatus(status), fingerprint=fingerprint,
            google_event_id=event_id, google_calendar_id=calendar_id,
        )
        repository.log_audit_event(
            session, event_type="diagnostic_synced", course_id=resolved_course_id,
            summary=f"Recorded Previous Week Diagnostic for {week_start} ({status})",
            details={"event_id": event_id, "week_start": week_start},
        )
    console.print("[green]Recorded.[/green]")


# --------------------------------------------------------------------------
# preferences
# --------------------------------------------------------------------------

@prefs_app.command("list")
def prefs_list(known: Annotated[bool, typer.Option("--known")] = False) -> None:
    if known:
        for spec in prefs_mod.KNOWN_PREFERENCES.values():
            console.print(
                f"[bold]{spec.key}[/bold] ({spec.category.value}) "
                f"default={spec.default!r} -- {spec.description}"
            )
        return
    with session_scope() as session:
        prefs = prefs_mod.list_prefs(session)
    if not prefs:
        console.print("No preferences set yet.")
        return
    table = Table(show_header=True)
    for col in ["key", "value", "scope", "course_id", "source"]:
        table.add_column(col)
    for p in prefs:
        table.add_row(p.key, json.dumps(p.value), p.scope.value, p.course_id or "-", p.source)
    console.print(table)


@prefs_app.command("set")
def prefs_set(
    key: Annotated[str, typer.Argument()],
    value: Annotated[str, typer.Argument()],
    course: Annotated[str | None, typer.Option("--course")] = None,
    force: Annotated[bool, typer.Option("--force", help="Allow setting an unknown key.")] = False,
) -> None:
    parsed_value: object = value
    for cast in (int, float):
        try:
            parsed_value = cast(value)
            break
        except ValueError:
            continue
    if value.lower() in ("true", "false"):
        parsed_value = value.lower() == "true"
    with session_scope() as session:
        prefs_mod.set_pref(session, key, parsed_value, course_id=course, allow_unknown=force)
        repository.log_audit_event(
            session, event_type="preference_set", course_id=course,
            summary=f"Set preference {key}={parsed_value!r}",
        )
    console.print(f"[green]Set[/green] {key} = {parsed_value!r}")


@prefs_app.command("get")
def prefs_get(
    key: Annotated[str, typer.Argument()],
    course: Annotated[str | None, typer.Option("--course")] = None,
) -> None:
    with session_scope() as session:
        value = prefs_mod.get_pref(session, key, course_id=course)
    console.print(json.dumps(value))


@prefs_app.command("unset")
def prefs_unset(
    key: Annotated[str, typer.Argument()],
    course: Annotated[str | None, typer.Option("--course")] = None,
) -> None:
    with session_scope() as session:
        found = prefs_mod.unset_pref(session, key, course_id=course)
    console.print("[green]Unset.[/green]" if found else "[yellow]No such active preference.[/yellow]")


if __name__ == "__main__":
    app()
