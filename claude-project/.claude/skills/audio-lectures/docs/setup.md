# Setup -- dependencies and the "another PC" workflow

## Why Kokoro

Kokoro-82M is a small, fast, openly-licensed (Apache-2.0) TTS model. On an
RTX 3080 it renders audio many times faster than real-time, which is the
whole point of the "generate faster than I can listen to it" goal -- a
week's worth of lectures across three courses should synthesize in a
couple of minutes, not require overnight batch runs. Its stock voice bank
includes several deep, narration-suited voices (default here: `am_fenrir`)
-- an original synthetic voice, not a clone of any real person. See
`../docs/style_guide.md`.

## Python dependencies (the "audio" extra)

- `torch` -- GPU inference; the CUDA build matters, see below.
- `kokoro` -- the TTS pipeline itself (wraps espeak-ng phonemization and
  the actual model).
- `soundfile` -- encodes the raw waveform to WAV before ffmpeg converts it
  to mp3.
- `numpy` -- audio array handling.

Install via:
```
uv add --optional audio torch kokoro soundfile numpy
uv sync --extra audio
```
`audio-lectures bootstrap-install --yes` runs exactly this. Note: the
default `torch` wheel PyPI resolves to may be CPU-only depending on
platform -- if `torch.cuda.is_available()` comes back `False` after
install despite having an NVIDIA GPU, reinstall torch from the
CUDA-specific index instead, e.g.:
```
uv pip install torch --index-url https://download.pytorch.org/whl/cu121
```
(pick the `cu1xx`/`cu12x` tag matching the installed CUDA toolkit/driver --
check the driver version with `nvidia-smi` first).

## System binaries

- **ffmpeg** -- used only to convert Kokoro's WAV output to mp3
  (`tts_engine.convert_wav_to_mp3`). Install: `winget install --id
  Gyan.FFmpeg -e`.
- **espeak-ng** -- Kokoro's phonemizer backend for English. Install:
  `winget install --id espeak-ng.espeak-ng -e`.

Both may need a new shell (or a PATH refresh) after installing before
`ffmpeg`/`espeak-ng` are found on PATH -- if `bootstrap-check` still shows
one as missing right after a winget install, open a fresh shell and check
again before assuming the install failed.

## Running on another PC (the "app" workflow)

Kokoro itself only needs to run once, on whichever machine has the GPU
(the 3080 desktop). To generate lectures from a different machine (a
laptop, away from the desktop):

1. On the 3080 machine, install and run a Kokoro-FastAPI-compatible server
   (a small wrapper app that exposes Kokoro behind an OpenAI-compatible
   `/v1/audio/speech` HTTP endpoint) so it's listening on the LAN, e.g.
   port 8880.
2. Find that machine's LAN IP (`ipconfig` on Windows).
3. From the other PC, run this project's `audio-lectures synthesize` with
   `--backend remote --server-url http://<that-ip>:8880` -- or set
   `AUDIO_LECTURES_TTS_MODE=remote` / `AUDIO_LECTURES_TTS_SERVER_URL=...`
   in `.env` to make that the default so you don't have to pass the flags
   every time.

`tts_engine.RemoteServerBackend` is the client side of this -- it POSTs
`{"model": "kokoro", "input": ..., "voice": ..., "speed": ...,
"response_format": "wav"}` and expects raw WAV bytes back, matching that
server's OpenAI-compatible speech-endpoint shape. Any local TTS server
exposing the same endpoint shape works without code changes; a genuinely
different API shape needs a new `TTSBackend` implementation added to
`tts_engine.py` (see the `TTSBackend` Protocol there).

## Output location

```
Desktop/Audio Lectures/<Course Code - Course Name>/<NN - Week of <date> - <topic>>.{txt,mp3}
```
plus one `.audio_lectures_manifest.json` at the root of that tree tracking
what's already been generated (see `manifest.py`). Override the root via
`AUDIO_LECTURES_OUTPUT_DIR` in `.env`, or `output_root` in
`config/audio_lectures.yaml`.
