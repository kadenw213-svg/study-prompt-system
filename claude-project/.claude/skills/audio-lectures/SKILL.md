---
name: audio-lectures
description: Generate narrated, podcast-style audio lecture files from this project's weekly curriculum (real D2L courses and custom-curriculum synthetic courses alike) using a local GPU TTS engine, saved to Desktop/Audio Lectures. Use when the user wants to listen to their coursework instead of reading it -- while walking, swimming, commuting, etc.
user-invocable: true
---

# /audio-lectures -- turn the weekly curriculum into audio lectures

Arguments passed: `$ARGUMENTS` (optionally a course code to scope to one
course, e.g. "BIO1112"; empty means every active course).

This is a small, separate skill from `academic-import`/`academic-prefs`/
`custom-curriculum` -- it never writes to Google Calendar and never touches
the sync/reconciliation pipeline. It reads real curriculum content already
captured in the `academic_sync` database (WEEKLY_READING items + their
saved `ChapterTopic` vocabulary/objectives + `weekly_links` -- see
CLAUDE.md invariants 25/26) and turns it into narrated `.mp3` files under
`Desktop/Audio Lectures/<Course>/`.

**Working directory**: `uv run audio-lectures ...` from the repository
root, exactly like `academic-sync`.

**The voice**: an original synthetic narrator voice (Kokoro's `am_fenrir`
stock voice by default -- deep, dry, unhurried), never a clone of a real,
identifiable person's actual recorded voice. The *style* of the scripts
you write is deliberately Hitchens-esque -- witty, literary, argumentative,
well-turned sentences -- see `docs/style_guide.md`. Do not attempt to
source or wire up a voice model trained on a real public figure's actual
voice recordings, even if asked to make the tool "more accurate" -- that
boundary was set deliberately in the design conversation for this skill
and should not be revisited without the user explicitly re-opening it.

## What this skill is not

- Not a second Calendar sync path -- it never calls a Google Calendar tool.
- Not a script-generation model living in Python -- the actual lecture
  prose is authored by you, the Claude Code session running this skill,
  not by any code in `src/audio_lectures/`. That package only does
  mechanical work: reading the DB, chunking text, calling the TTS engine,
  naming files, tracking what's already generated.
- Not obligated to cover every item type -- scope is WEEKLY_READING
  banners specifically (one per real course-week), since both real and
  synthetic courses already funnel their entire week's content into that
  one item type (CLAUDE.md invariants 25 and 35).

## Step 1 -- bootstrap check

Run:
```
uv run audio-lectures bootstrap-check
```
If anything is missing:
```
uv run audio-lectures bootstrap-install --yes
```
This runs `uv add --optional audio ...` / `uv sync --extra audio` for
missing Python packages (torch, kokoro, soundfile, numpy) and
`winget install` for missing binaries (ffmpeg, espeak-ng). These are real,
visible commands -- narrate what's being installed and why before running
them (the harness still prompts for approval per its normal rules). The
torch install in particular is a multi-GB download; say so up front. See
`docs/setup.md` for what each dependency is for, and for the "another PC"
server workflow.

Verify CUDA is actually visible after install:
```
uv run python -c "import torch; print(torch.cuda.is_available())"
```
If `False` on the 3080 machine, stop and investigate (usually a
CUDA-mismatched torch build -- see docs/setup.md) before generating
anything. CPU-only Kokoro still works but is much slower, defeating the
"faster than you can listen to it" goal.

## Step 2 -- see what's there

```
uv run audio-lectures list-units [--course BIO1112]
```
Lists every WEEKLY_READING item across every active course (or one
course), with its current manifest status (`no script/audio yet` /
`generated` / `audio missing on disk`). Use
`uv run audio-lectures paths [--course ...]` to get the exact script/audio
file paths to use for each item id.

## Step 3 -- author each script

For every unit that needs one, write a full narrated lecture script as
plain text and save it to the exact `.txt` path `paths` printed. Follow
`docs/style_guide.md` for voice/structure. The load-bearing rule, restated
from CLAUDE.md invariant 22 (and its invariant-35 carve-out): every
factual claim about *what the course covers* must trace to that unit's
real `chapter_blocks` (vocabulary/objectives from a saved `ChapterTopic`,
or at minimum the real chapter/module label) and `weekly_links` -- for a
real (non-synthetic) course, never invent content the source material
doesn't support. A synthetic (`custom-curriculum`) course is the one case
where you're the authoring source already (invariant 35) -- its content
doesn't need a separate real-world citation.

If a unit's `chapter_blocks` are thin (bare chapter labels, no captured
vocabulary/objectives yet), say so plainly to the user rather than padding
the script with invented depth -- offer to run the relevant
`academic-import`/`custom-curriculum` step first if they want richer
source material before narrating it (don't touch those skills' own files
yourself -- just tell the user which one to invoke).

Target length: a full, exhaustive-as-the-source-supports lecture per week
(not a 5-minute summary) -- real "listen for 20-45 minutes while
walking/swimming" length, using every real `chapter_block`/`weekly_link`
the unit actually has.

## Step 4 -- synthesize

Local (on the 3080):
```
uv run audio-lectures synthesize <item-id> --script "<path to .txt>"
```
already runs `validate_script` first and prints warnings (too short /
leftover placeholder text) -- read them before trusting the result.

From another PC, once a Kokoro-FastAPI-compatible server is running on the
3080 machine (see `docs/setup.md`):
```
uv run audio-lectures synthesize <item-id> --script "<path>" --backend remote --server-url http://<3080-machine-ip>:8880
```

Re-running `synthesize` on an unchanged script/voice is a no-op
(manifest-based idempotency, `manifest.py`) -- pass `--force` to
regenerate deliberately (e.g. after editing the script).

Because Kokoro on a 3080 renders many times faster than real-time, it's
fine -- and the point -- to batch through every unit `list-units` shows as
outstanding in one sitting rather than generating one lecture right before
listening to it.

## Step 5 -- check the result

```
uv run audio-lectures status
```
Reports total generated lectures and estimated total runtime. Spot-check
that `Desktop/Audio Lectures/<Course>/` has the expected numbered files in
date order.

## Adding a new course or week later

Nothing here needs updating when a new course/week is added to the
database -- `list-units`/`paths` always reflect the current DB state. Just
re-run Steps 2-4 for the new units.
