from __future__ import annotations

import io
import wave

import pytest

from audio_lectures.tts_engine import concatenate_wav_chunks


def _make_wav(seconds: float, framerate: int = 24000) -> bytes:
    n_frames = int(seconds * framerate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(framerate)
        writer.writeframes(b"\x00\x00" * n_frames)
    return buffer.getvalue()


def test_concatenate_single_chunk_returns_equivalent_audio():
    chunk = _make_wav(1.0)
    result = concatenate_wav_chunks([chunk])
    with wave.open(io.BytesIO(result), "rb") as reader:
        assert reader.getnframes() == 24000


def test_concatenate_multiple_chunks_inserts_silence_between_them():
    chunk = _make_wav(1.0)
    result = concatenate_wav_chunks([chunk, chunk], pause_ms=500)
    with wave.open(io.BytesIO(result), "rb") as reader:
        # 1s + 1s of real audio + 0.5s of inserted silence == 2.5s == 60000 frames.
        assert reader.getnframes() == 60000


def test_concatenate_no_silence_after_final_chunk():
    chunk = _make_wav(0.5)
    result = concatenate_wav_chunks([chunk], pause_ms=1000)
    with wave.open(io.BytesIO(result), "rb") as reader:
        assert reader.getnframes() == 12000


def test_concatenate_raises_on_empty_input():
    with pytest.raises(ValueError):
        concatenate_wav_chunks([])
