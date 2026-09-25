"""CLI entry point for the audio-lectures skill.

Deliberately a second, separate Typer app/entry point from `academic-sync`
(see pyproject.toml's `[project.scripts]`) -- this reads that project's
database read-only but is otherwise its own concern (output folder, TTS
engine, manifest). The /audio-lectures skill drives this CLI the same way
/academic-import drives `academic-sync`: this file has no judgment calls
in it (what to say in a script, which weeks are worth generating first),
only mechanical operations -- see docs/style_guide.md for where the
judgment happens.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from academic_sync.db import repository
from academic_sync.db.session import session_scope
from audio_lectures import bootstrap
from audio_lectures.config import get_config, get_output_root
from audio_lectures.content import LectureUnit, list_lecture_units
from audio_lectures.manifest import (
    compute_content_hash,
    load_manifest,
    needs_regeneration,
    record_generation,
    save_manifest,
)
from audio_lectures.naming import lecture_filename, output_dir_for_course, script_filename
from audio_lectures.script_writer import chunk_script_for_tts, estimate_duration_seconds, validate_script
from audio_lectures.tts_engine import (
    KokoroLocalBackend,
    RemoteServerBackend,
    TTSBackend,
    convert_wav_to_mp3,
    synthesize_script,
)

app = typer.Typer(help="Generate narrated audio lectures from this project's weekly curriculum.")
console = Console()


def _units_by_course(units: list[LectureUnit]) -> dict[str, list[LectureUnit]]:
    by_course: dict[str, list[LectureUnit]] = {}
    for unit in units:
        by_course.setdefault(unit.course_id, []).append(unit)
    return by_course


@app.command("bootstrap-check")
def bootstrap_check_cmd() -> None:
    """Reports which of Kokoro/torch/soundfile/numpy, ffmpeg, and
    espeak-ng are missing, plus whether CUDA is visible to torch."""
    report = bootstrap.check()
    table = Table(title="audio-lectures dependency check")
    table.add_column("Component")
    table.add_column("Status")
    for package in ("torch", "kokoro", "soundfile", "numpy"):
        status = "[red]missing[/red]" if package in report.missing_python_packages else "[green]ok[/green]"
        table.add_row(package, status)
    for binary in ("ffmpeg", "espeak-ng"):
        status = "[red]missing[/red]" if binary in report.missing_binaries else "[green]ok[/green]"
        table.add_row(binary, status)
    cuda_status = (
        "unknown (torch not installed)"
        if report.cuda_available is None
        else ("[green]available[/green]" if report.cuda_available else "[yellow]CPU only[/yellow]")
    )
    table.add_row("CUDA", cuda_status)
    console.print(table)
    if not report.is_complete:
        console.print("\n[yellow]Missing dependencies. Suggested commands:[/yellow]")
        for command in bootstrap.install_commands(report):
            console.print(f"  {command}")


@app.command("bootstrap-install")
def bootstrap_install_cmd(
    yes: Annotated[bool, typer.Option("--yes", help="Actually run the install commands.")] = False,
) -> None:
    """Prints the install commands for whatever bootstrap-check found
    missing; only runs them with --yes. Stops at the first failure."""
    report = bootstrap.check()
    if report.is_complete:
        console.print("[green]All dependencies already present.[/green]")
        return
    commands = bootstrap.install_commands(report)
    if not yes:
        console.print("[yellow]Would run:[/yellow]")
        for command in commands:
            console.print(f"  {command}")
        console.print("\nRe-run with --yes to actually install.")
        return
    for command in commands:
        console.print(f"[cyan]$ {command}[/cyan]")
        result = bootstrap.run_command(command)
        console.print(result.stdout)
        if result.returncode != 0:
            console.print(f"[red]Command failed (exit {result.returncode}):[/red]\n{result.stderr}")
            raise typer.Exit(1)


@app.command("list-units")
def list_units_cmd(
    course: Annotated[str | None, typer.Option("--course", help="Course id or course code.")] = None,
    include_inactive: Annotated[bool, typer.Option("--include-inactive")] = False,
) -> None:
    """Lists every candidate lecture unit (one per WEEKLY_READING item),
    with each unit's up-to-date/needs-generation status against the
    manifest -- run this before authoring scripts to see what's left."""
    output_root = get_output_root()
    manifest = load_manifest(output_root)
    with session_scope() as session:
        units = list_lecture_units(session, course_id=course, include_inactive=include_inactive)

    table = Table(title="Lecture units")
    table.add_column("Item ID")
    table.add_column("Course")
    table.add_column("Week of")
    table.add_column("Topic")
    table.add_column("Status")
    for by_course in _units_by_course(units).values():
        for unit in by_course:
            entry = manifest.get(unit.unit_key)
            status = "no script/audio yet" if entry is None else "generated"
            if entry is not None and not Path(entry.audio_path).exists():
                status = "audio missing on disk"
            table.add_row(
                unit.item_id,
                unit.course_code,
                unit.week_start.isoformat() if unit.week_start else "-",
                unit.short_title,
                status,
            )
    console.print(table)


@app.command("paths")
def paths_cmd(
    course: Annotated[str | None, typer.Option("--course", help="Course id or course code.")] = None,
) -> None:
    """Prints the exact script/audio file path each lecture unit should
    use, so a skill session can write the script to the right place before
    calling `synthesize`."""
    with session_scope() as session:
        units = list_lecture_units(session, course_id=course, include_inactive=True)
        by_course_units = _units_by_course(units)
        courses = {c.id: c for c in repository.list_courses(session)}
    output_root = get_output_root()
    for course_id, course_units in by_course_units.items():
        course_obj = courses[course_id]
        course_dir = output_dir_for_course(output_root, course_obj)
        for index, unit in enumerate(course_units, start=1):
            console.print(f"{unit.item_id}\t{course_dir / script_filename(unit, index)}")
            console.print(f"{unit.item_id}\t{course_dir / lecture_filename(unit, index)}")


def _resolve_backend(backend: str, server_url: str | None) -> TTSBackend:
    config = get_config()
    mode = backend or config.tts.mode
    if mode == "remote":
        url = server_url or config.tts.server_url
        if not url:
            console.print("[red]--backend remote requires --server-url (or config tts.server_url).[/red]")
            raise typer.Exit(1)
        return RemoteServerBackend(base_url=url)
    return KokoroLocalBackend()


@app.command("synthesize")
def synthesize_cmd(
    item_id: Annotated[str, typer.Argument(help="The WEEKLY_READING item id from `list-units`.")],
    script: Annotated[Path, typer.Option("--script", help="Path to the authored lecture script (.txt).")],
    voice: Annotated[str | None, typer.Option("--voice")] = None,
    speed: Annotated[float | None, typer.Option("--speed")] = None,
    backend: Annotated[str, typer.Option("--backend", help="'local' or 'remote'.")] = "local",
    server_url: Annotated[str | None, typer.Option("--server-url")] = None,
    force: Annotated[bool, typer.Option("--force", help="Regenerate even if unchanged.")] = False,
) -> None:
    """Renders one lecture unit's authored script to audio and saves it
    under Desktop/Audio Lectures/<course>/, skipping the render if the
    script/voice/speed are unchanged from the last run (see manifest.py)."""
    config = get_config()
    voice_id = voice or config.voice.voice_id
    voice_speed = speed if speed is not None else config.voice.speed

    with session_scope() as session:
        units = list_lecture_units(session, include_inactive=True)
        unit = next((u for u in units if u.item_id == item_id), None)
        if unit is None:
            console.print(f"[red]No WEEKLY_READING item found with id {item_id}.[/red]")
            raise typer.Exit(1)
        course = repository.get_course(session, unit.course_id)

    if not script.exists():
        console.print(f"[red]Script file not found: {script}[/red]")
        raise typer.Exit(1)
    script_text = script.read_text(encoding="utf-8")

    warnings = validate_script(script_text, min_words=config.script.min_script_words)
    for warning in warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    output_root = get_output_root()
    manifest = load_manifest(output_root)
    content_hash = compute_content_hash(script_text, voice_id, voice_speed)
    if not force and not needs_regeneration(manifest, unit.unit_key, content_hash):
        console.print(f"[green]Up to date, skipping:[/green] {unit.short_title}")
        return

    assert course is not None
    course_dir = output_dir_for_course(output_root, course)
    all_units = [u for u in units if u.course_id == course.id]
    index = all_units.index(unit) + 1
    audio_path = course_dir / lecture_filename(unit, index)
    saved_script_path = course_dir / script_filename(unit, index)
    saved_script_path.write_text(script_text, encoding="utf-8")

    chunks = chunk_script_for_tts(script_text, max_chars=config.script.max_tts_chunk_chars)
    console.print(f"Synthesizing {len(chunks)} chunk(s) for: {unit.short_title}")
    tts_backend = _resolve_backend(backend, server_url)
    wav_bytes = synthesize_script(chunks, tts_backend, voice=voice_id, speed=voice_speed)
    convert_wav_to_mp3(wav_bytes, audio_path)

    duration = estimate_duration_seconds(script_text, config.script.words_per_minute_estimate)
    record_generation(
        manifest,
        unit_key=unit.unit_key,
        content_hash=content_hash,
        audio_path=audio_path,
        script_path=saved_script_path,
        voice_id=voice_id,
        generated_at=dt.datetime.now(dt.UTC).isoformat(),
        duration_seconds=duration,
    )
    save_manifest(output_root, manifest)
    console.print(f"[green]Wrote:[/green] {audio_path} (~{duration / 60:.1f} min estimated)")


@app.command("status")
def status_cmd() -> None:
    """Summarizes what's already generated across every course."""
    output_root = get_output_root()
    manifest = load_manifest(output_root)
    total_seconds = sum(e.duration_seconds or 0.0 for e in manifest.values())
    console.print(f"Output root: {output_root}")
    console.print(f"Generated lectures: {len(manifest)}")
    console.print(f"Total estimated runtime: {total_seconds / 60:.1f} minutes")


if __name__ == "__main__":
    app()
