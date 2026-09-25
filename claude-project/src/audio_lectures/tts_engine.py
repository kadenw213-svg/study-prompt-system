"""Local/remote speech synthesis.

Heavy ML dependencies (torch, kokoro, soundfile, numpy) are imported
lazily inside the functions/methods that actually need them, so importing
this module -- and every other module in this package -- never requires
them to be installed. Only `KokoroLocalBackend`'s first real call does.
See bootstrap.py for the install step and docs/setup.md for why Kokoro was
chosen (fast enough on a 3080 to generate an hour of narration well before
you could listen to it).

Narrator voice: this project deliberately uses one of Kokoro's own stock
voices -- an original synthetic voice -- never a clone of a real,
identifiable person's actual recorded voice. See docs/style_guide.md.
"""

from __future__ import annotations

import io
import json
import subprocess
import urllib.request
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class TTSBackend(Protocol):
    def synth_chunk(self, text: str, voice: str, speed: float) -> bytes:
        """Returns mono 16-bit PCM WAV bytes for one chunk of text."""
        ...


@dataclass
class KokoroLocalBackend:
    """Runs Kokoro in-process on this machine's GPU (falls back to CPU if
    CUDA isn't available -- see bootstrap.check()'s `cuda_available`).
    Lazily builds the pipeline on first use so importing this module never
    requires torch/kokoro to be installed."""

    lang_code: str = "a"  # Kokoro's code for American English
    _pipeline: object | None = None

    def _get_pipeline(self) -> object:
        if self._pipeline is None:
            import torch
            from kokoro import KPipeline

            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._pipeline = KPipeline(lang_code=self.lang_code, device=device)
        return self._pipeline

    def synth_chunk(self, text: str, voice: str, speed: float) -> bytes:
        import numpy as np
        import soundfile as sf

        pipeline = self._get_pipeline()
        audio_segments = []
        for _graphemes, _phonemes, audio in pipeline(text, voice=voice, speed=speed):  # type: ignore[operator]
            audio_segments.append(audio)
        if not audio_segments:
            audio_segments = [np.zeros(1, dtype="float32")]
        audio = np.concatenate(audio_segments)
        buffer = io.BytesIO()
        sf.write(buffer, audio, samplerate=24000, format="WAV", subtype="PCM_16")
        return buffer.getvalue()


@dataclass
class RemoteServerBackend:
    """Calls a Kokoro-FastAPI-compatible OpenAI `/v1/audio/speech` endpoint
    running on another machine on the LAN -- e.g. generating on the 3080
    desktop while running the skill itself from a laptop. See
    docs/setup.md for standing that server up."""

    base_url: str
    timeout_seconds: float = 120.0

    def synth_chunk(self, text: str, voice: str, speed: float) -> bytes:
        payload = json.dumps(
            {
                "model": "kokoro",
                "input": text,
                "voice": voice,
                "speed": speed,
                "response_format": "wav",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/v1/audio/speech",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
            return response.read()


def concatenate_wav_chunks(chunks: list[bytes], pause_ms: int = 350) -> bytes:
    """Joins several mono 16-bit PCM WAV byte-strings into one, inserting a
    short silence between chunks so sentence-boundary chunking (see
    script_writer.chunk_script_for_tts) doesn't run words together."""
    if not chunks:
        raise ValueError("No audio chunks to concatenate.")
    readers = [wave.open(io.BytesIO(c), "rb") for c in chunks]
    params = readers[0].getparams()
    silence_frames = int(params.framerate * pause_ms / 1000)
    silence = b"\x00\x00" * silence_frames * params.nchannels

    output = io.BytesIO()
    with wave.open(output, "wb") as out:
        out.setparams(params)
        for index, reader in enumerate(readers):
            out.writeframes(reader.readframes(reader.getnframes()))
            reader.close()
            if index != len(readers) - 1:
                out.writeframes(silence)
    return output.getvalue()


def synthesize_script(chunks: list[str], backend: TTSBackend, voice: str, speed: float = 1.0) -> bytes:
    """Synthesizes every chunk and returns one concatenated WAV file."""
    audio_chunks = [backend.synth_chunk(chunk, voice, speed) for chunk in chunks]
    return concatenate_wav_chunks(audio_chunks)


def convert_wav_to_mp3(wav_bytes: bytes, mp3_path: Path) -> None:
    """Shells out to ffmpeg (must be on PATH -- see bootstrap.py) rather
    than pulling in a Python MP3 encoder dependency."""
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "wav",
            "-i",
            "pipe:0",
            "-codec:a",
            "libmp3lame",
            "-qscale:a",
            "2",
            str(mp3_path),
        ],
        input=wav_bytes,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed converting {mp3_path.name}: {process.stderr.decode(errors='replace')}"
        )
