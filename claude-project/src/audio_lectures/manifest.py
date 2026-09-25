"""Idempotency for generated audio files -- a JSON manifest keyed by
`LectureUnit.unit_key`, so re-running `synthesize` on an unchanged week
never re-renders audio that's already sitting on disk.

Deliberately its own file next to the generated audio (not academic_sync's
`SyncRecord` table) -- audio generation is a completely separate concern
from Calendar sync idempotency, the same reasoning shift-sync uses for
staying out of academic_sync's data model (see CLAUDE.md's "Where the
skills fit"). One manifest file lives at the root of the whole output
tree, covering every course, so `status` can report across all of them
without walking per-course files.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

MANIFEST_FILENAME = ".audio_lectures_manifest.json"


@dataclass
class ManifestEntry:
    unit_key: str
    content_hash: str
    audio_path: str
    script_path: str
    voice_id: str
    generated_at: str
    duration_seconds: float | None = None


def compute_content_hash(script_text: str, voice_id: str, speed: float) -> str:
    """Changes whenever the script text, voice, or speed changes -- any of
    those three genuinely changes what the resulting audio would sound
    like, so any of them should trigger regeneration."""
    payload = f"{script_text}\x00{voice_id}\x00{speed}".encode()
    return hashlib.sha256(payload).hexdigest()


def load_manifest(output_root: Path) -> dict[str, ManifestEntry]:
    path = output_root / MANIFEST_FILENAME
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {key: ManifestEntry(**value) for key, value in raw.items()}


def save_manifest(output_root: Path, manifest: dict[str, ManifestEntry]) -> None:
    path = output_root / MANIFEST_FILENAME
    raw = {key: asdict(entry) for key, entry in manifest.items()}
    path.write_text(json.dumps(raw, indent=2, sort_keys=True), encoding="utf-8")


def needs_regeneration(manifest: dict[str, ManifestEntry], unit_key: str, new_hash: str) -> bool:
    """True when there's no prior entry, the script/voice/speed changed
    since the last render, or the previously-recorded audio file no longer
    exists on disk (moved or deleted by the user) -- regenerate rather than
    silently leaving a manifest entry that points at nothing."""
    entry = manifest.get(unit_key)
    if entry is None:
        return True
    if entry.content_hash != new_hash:
        return True
    return not Path(entry.audio_path).exists()


def record_generation(
    manifest: dict[str, ManifestEntry],
    *,
    unit_key: str,
    content_hash: str,
    audio_path: Path,
    script_path: Path,
    voice_id: str,
    generated_at: str,
    duration_seconds: float | None = None,
) -> None:
    manifest[unit_key] = ManifestEntry(
        unit_key=unit_key,
        content_hash=content_hash,
        audio_path=str(audio_path),
        script_path=str(script_path),
        voice_id=voice_id,
        generated_at=generated_at,
        duration_seconds=duration_seconds,
    )
