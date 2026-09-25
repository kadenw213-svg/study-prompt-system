from __future__ import annotations

from pathlib import Path

from audio_lectures.manifest import (
    ManifestEntry,
    compute_content_hash,
    load_manifest,
    needs_regeneration,
    record_generation,
    save_manifest,
)


def test_content_hash_changes_when_script_text_changes():
    a = compute_content_hash("Hello world", "am_fenrir", 1.0)
    b = compute_content_hash("Hello there", "am_fenrir", 1.0)
    assert a != b


def test_content_hash_changes_when_voice_changes():
    a = compute_content_hash("Hello world", "am_fenrir", 1.0)
    b = compute_content_hash("Hello world", "am_michael", 1.0)
    assert a != b


def test_content_hash_changes_when_speed_changes():
    a = compute_content_hash("Hello world", "am_fenrir", 1.0)
    b = compute_content_hash("Hello world", "am_fenrir", 1.1)
    assert a != b


def test_content_hash_stable_for_identical_input():
    assert compute_content_hash("x", "v", 1.0) == compute_content_hash("x", "v", 1.0)


def test_needs_regeneration_true_when_no_prior_entry():
    assert needs_regeneration({}, "unit-1", "hash-1") is True


def test_needs_regeneration_false_when_hash_matches_and_file_exists(tmp_path: Path):
    audio = tmp_path / "lecture.mp3"
    audio.write_bytes(b"fake mp3 data")
    manifest: dict[str, ManifestEntry] = {}
    record_generation(
        manifest, unit_key="unit-1", content_hash="hash-1", audio_path=audio,
        script_path=tmp_path / "lecture.txt", voice_id="am_fenrir", generated_at="2026-09-14T00:00:00Z",
    )
    assert needs_regeneration(manifest, "unit-1", "hash-1") is False


def test_needs_regeneration_true_when_hash_changed(tmp_path: Path):
    audio = tmp_path / "lecture.mp3"
    audio.write_bytes(b"fake mp3 data")
    manifest: dict[str, ManifestEntry] = {}
    record_generation(
        manifest, unit_key="unit-1", content_hash="hash-1", audio_path=audio,
        script_path=tmp_path / "lecture.txt", voice_id="am_fenrir", generated_at="2026-09-14T00:00:00Z",
    )
    assert needs_regeneration(manifest, "unit-1", "hash-2") is True


def test_needs_regeneration_true_when_audio_file_missing(tmp_path: Path):
    audio = tmp_path / "deleted_by_user.mp3"
    manifest: dict[str, ManifestEntry] = {}
    record_generation(
        manifest, unit_key="unit-1", content_hash="hash-1", audio_path=audio,
        script_path=tmp_path / "lecture.txt", voice_id="am_fenrir", generated_at="2026-09-14T00:00:00Z",
    )
    assert needs_regeneration(manifest, "unit-1", "hash-1") is True


def test_save_and_load_manifest_round_trips(tmp_path: Path):
    manifest: dict[str, ManifestEntry] = {}
    record_generation(
        manifest, unit_key="unit-1", content_hash="hash-1", audio_path=tmp_path / "a.mp3",
        script_path=tmp_path / "a.txt", voice_id="am_fenrir", generated_at="2026-09-14T00:00:00Z",
        duration_seconds=930.5,
    )
    save_manifest(tmp_path, manifest)
    reloaded = load_manifest(tmp_path)
    assert reloaded["unit-1"].content_hash == "hash-1"
    assert reloaded["unit-1"].duration_seconds == 930.5


def test_load_manifest_returns_empty_dict_when_missing(tmp_path: Path):
    assert load_manifest(tmp_path) == {}
