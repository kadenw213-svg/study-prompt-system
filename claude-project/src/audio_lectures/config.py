"""Configuration for the audio-lectures skill.

Deliberately a separate, small config surface from academic_sync.config --
this skill reads academic_sync's database (courses/items/chapter topics)
but has its own output location, TTS engine choice, and voice settings
that have nothing to do with Calendar sync. Same "where are things on
disk" / "what did the engineering defaults say" scope as academic_sync's
own config.py -- it never talks to the network itself either; the actual
TTS calls live in tts_engine.py.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "audio_lectures.yaml"
# Desktop\Audio Lectures -- a real, visible folder the user asked for by
# name, not a path buried inside the repo.
DEFAULT_OUTPUT_ROOT = Path.home() / "Desktop" / "Audio Lectures"


class VoiceConfig(BaseModel):
    """An original synthetic narrator voice -- deliberately never a clone
    of a real, identifiable person's actual recorded voice. See
    docs/style_guide.md. `voice_id` is one of Kokoro's own stock voices
    (default: a deep American-English male voice suited to long-form
    narration)."""

    voice_id: str = "am_fenrir"
    speed: float = 1.0
    lang_code: str = "a"  # Kokoro's code for American English


class TTSServerConfig(BaseModel):
    """`mode="local"` runs Kokoro in-process on this machine's own GPU.
    `mode="remote"` calls an OpenAI-speech-API-compatible server (e.g.
    Kokoro-FastAPI) running on another machine on the LAN -- the workflow
    for generating on the 3080 desktop while listening/working from a
    laptop, or vice versa. See docs/setup.md."""

    mode: str = "local"
    server_url: str | None = None


class ScriptConfig(BaseModel):
    max_tts_chunk_chars: int = 400
    words_per_minute_estimate: int = 165
    min_script_words: int = 250


class AudioLecturesConfig(BaseModel):
    output_root: str = str(DEFAULT_OUTPUT_ROOT)
    output_format: str = "mp3"
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    tts: TTSServerConfig = Field(default_factory=TTSServerConfig)
    script: ScriptConfig = Field(default_factory=ScriptConfig)


class Settings(BaseSettings):
    """Environment-derived overrides. See .env.example for the full list."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_prefix="AUDIO_LECTURES_")

    output_dir: str | None = None
    tts_mode: str | None = None
    tts_server_url: str | None = None
    voice_id: str | None = None


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_config() -> AudioLecturesConfig:
    settings = get_settings()
    raw = _load_yaml(DEFAULT_CONFIG_PATH)
    config = AudioLecturesConfig.model_validate(raw)
    if settings.output_dir:
        config.output_root = settings.output_dir
    if settings.tts_mode:
        config.tts.mode = settings.tts_mode
    if settings.tts_server_url:
        config.tts.server_url = settings.tts_server_url
    if settings.voice_id:
        config.voice.voice_id = settings.voice_id
    return config


def get_output_root() -> Path:
    root = Path(get_config().output_root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def clear_caches() -> None:
    """Test helper: force the next get_settings()/get_config() call to rebuild."""
    get_settings.cache_clear()
    get_config.cache_clear()
