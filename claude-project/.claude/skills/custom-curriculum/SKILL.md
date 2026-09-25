---
name: custom-curriculum
description: Build a fully synthetic, self-directed "class" on a topic the user describes -- no real D2L source -- as weekly overview banners carrying a full chapter-by-chapter teaching outline (ordered objectives + key terms), so the GPT study system can teach it as a complete, coherent course. Output goes to Google Calendar, a shareable .ics file for the study-prompt-system repo's premade courses library, or both. Use when the user wants to study a topic on their own schedule, or build a premade course for others.
user-invocable: true
---

# /custom-curriculum -- build a synthetic self-directed class

Arguments passed: `$ARGUMENTS` (may be empty, or a topic hint like "linear
algebra" / "organic chemistry basics").

This skill authors a complete course -- a week-by-week sequence **and a full
teaching outline for every chapter** -- for a class that doesn't exist
anywhere but here, registers it in the same local database real scraped
courses live in, and outputs it to Google Calendar and/or a `.ics` file in
exactly the format `academic-import` produces. The GPT study system (the
`study-prompt-system` repo's `boot.md` + `engine/`/`modes/` rule files, one
level above `claude-project/`) reads each weekly banner's THIS WEEK section
as its curriculum for that week, then teaches it in teaching mode.
Self-study courses are never part of its Automatic mode; the user opens
them deliberately. Read `CLAUDE.md` invariant 35 before your first run in a
session -- it's the authoritative carve-out this skill operates under.

**Working directory**: the `academic-sync` project at the repository root.
All CLI commands are `uv run academic-sync ...` via Bash.

**Live tools**: `mcp__claude_ai_Google_Calendar__*`, in Step 4's Calendar
path only. Nothing here touches D2L or a browser.

**What this skill produces**: `WEEKLY_READING` banners only, plus one
`chapter-topic-add` row per chapter, which `render` automatically pulls into
each banner's THIS WEEK. **No quizzes, exams, homework, assignments,
deadlines, or meetings -- ever** (user-directed 2026-09-25). Practice comes
from the GPT system's own teaching mode (comprehension questions, chapter
checkpoints, scored batches).

## Step 0: gather inputs

Ask directly, don't guess:

1. **Topic and academic level** -- e.g. "Linear algebra, intro/undergraduate".
2. **Course length in weeks** -- an integer. No default.
3. **Pacing tier** -- **Light** ~2-4 h/week · **Moderate** ~5-8 h/week ·
   **Intensive** ~9-14 h/week (rough ranges, say so).
4. **Start date** -- default to the upcoming Monday and say so plainly.
5. **Output** -- `Calendar`, `.ics file` (saved to
   `github_study_prompt/courses/` for the premade library), or `both`. Ask
   every time; no default.

## Step 1: author the course (local, no writes yet)

**Chapters.** Break the subject into numbered chapters in genuine
prerequisite order (prerequisites before what depends on them), the way a
well-built course at that level is structured. Chapter numbers run 1..N
across the whole course.

**Weeks.** Assign chapters to real calendar weeks, calibrated to
`weeks x pacing tier`. One `WEEKLY_READING` banner per calendar week, never
per chapter. A long chapter can span consecutive weeks; a week can hold
more than one short chapter. Each week's label uses the `"Chapter N: Topic;
Chapter M: Topic"` shape `weekly-reading-add --chapters` expects.

**Chapter outline -- this is where the course's coherence lives.** For every
chapter, write:

- **Title**: a short, specific name ("Linear Independence and Span", not
  "More Vectors").
- **Objectives**: 6-12, **in teaching order** -- the order the GPT tutor
  should teach them in, each building on the last. Each one is one concrete,
  teachable, checkable learning goal naming the specific concept or skill
  and the depth expected ("Compute the determinant of a 3x3 matrix by
  cofactor expansion", not "Understand determinants"). Include:
  - the chapter's core concepts and how they connect;
  - for quantitative subjects, the specific procedures to perform;
  - the standard misconceptions or edge cases worth teaching explicitly
    ("Distinguish correlation from causation using a confounder example");
  - when the chapter depends on an earlier one, one opening objective that
    names the link ("Recall matrix multiplication from Chapter 3 and apply it
    to composition of transformations").
- **Key terms**: 8-15 terms the chapter introduces or relies on.

This is authored content for a synthetic course only (invariant 35) -- real
depth, in the right order, at the stated level. It is never presented as an
instructor's material; every event carries the `SYNTHESIZED CURRICULUM` tag.
Keep one week's banner comfortably under Calendar's ~8,000-character
description limit (roughly 3 chapters at full depth); a week that would
exceed that gets fewer chapters. `render` truncates visibly if it has to, but
that means the plan was too dense.

## Step 2: present for explicit approval (mandatory gate)

Show everything before any write: topic, level, weeks, pacing tier + hour
range, start date, output choice, the week-by-week plan (one line per week
with its date range and chapters), then **every chapter's full outline**
(title, ordered objectives, key terms).

The user's approval *is* what makes this content legitimate for this course
type (CLAUDE.md invariant 35). Don't skip it or proceed on an ambiguous or
partial yes. Apply requested edits and re-show the changed parts.

## Step 3: on approval, write to the database

1. Register the course once:
   ```
   uv run academic-sync course add \
     --code "<topic name>" --name "<topic name>" --term "<term>" \
     --start <start_date> --end <computed_end_date> --synthetic
   ```
   Never pass `--instructor`/`--instructor-contact` (a synthetic course has no
   CONTACT section). Run exactly once -- re-running `course add` without
   `--synthetic` would clear the flag.
2. Every chapter:
   ```
   uv run academic-sync chapter-topic-add --course <course_id> \
     --chapter "Chapter N" --title "<title>" \
     --vocabulary "<term>, <term>, ..." \
     --objective "<objective 1>" --objective "<objective 2>" ...
   ```
   Objectives in teaching order. **Never pass `--exhaustive`** -- that flag
   certifies a real platform's complete topic list and has no meaning here.
3. Every week:
   ```
   uv run academic-sync weekly-reading-add \
     --course <course_id> --week-start <date> --week-end <date> \
     --chapters "Chapter N: <title>; Chapter M: <title>"
   ```
   Use the same chapter titles as step 2 so each banner's label matches its
   saved topic. All three commands are idempotent -- re-running corrects the
   same row, never duplicates.

## Step 4: output

**Calendar path.** Reuse `academic-import`'s Step 5 flow exactly: for each
banner, `uv run academic-sync render <item_id> --json` (it auto-pulls the
saved chapter topics into THIS WEEK) → `mcp__claude_ai_Google_Calendar__
create_event` → `uv run academic-sync record-sync <item_id> --event-id <id>
--calendar-id <calendar_id>` right after each successful write. Batch
independent creates.

**`.ics` path.**
1. `uv run academic-sync export-ics --course <course_id> --out
   github_study_prompt/courses/<slug>.ics` (`slug` = lowercase-hyphenated
   topic, e.g. `intro-statistics.ics`).
2. Add one row to `github_study_prompt/courses/catalog.md`'s table: title,
   level, weeks, pacing, chapters, file, one-line description.
3. **Never commit or push it.** Tell the user the file path, and that it goes
   public only after they've audited it and explicitly said to publish.

Either way, spot-check one rendered banner before calling it done: it must
start with `SYNTHESIZED CURRICULUM` and show each chapter as `Chapter N —
Title:` with its key terms and ordered objectives as bullets. A bare chapter
line means a `chapter-topic-add` label didn't match (use the same "Chapter N"
number in both commands).

## Step 5: close out

Tell the user: the course id, chapter and week counts, which output(s) were
produced (events synced, and/or the `.ics` path + catalog row awaiting their
audit), and that in the study chat it appears under **Self-study courses**,
opened directly (never via Automatic).

## Rules that apply throughout (see CLAUDE.md invariant 35)

- Footprint: `WEEKLY_READING` banners + `chapter-topic-add` rows only. Never
  a quiz, exam, homework, assignment, deadline, meeting, or lab item.
- Never set `instructor`/`instructor_contact`; never pass `--exhaustive`.
- Never set `is_synthetic = True` on a course with any real scraped content,
  and never `False` on one this skill created.
- Every other CLAUDE.md invariant still applies -- no guests, no Meet links,
  idempotency by natural key, no dates outside the approved outline.
