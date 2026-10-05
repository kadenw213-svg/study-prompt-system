---
name: custom-curriculum
description: Build a fully synthetic, self-directed "class" on a topic the user describes -- no real D2L source -- as weekly overview banners that list each week's chapters with real readings found online (OpenStax, LibreTexts, MIT OCW, university course pages), plus a full objectives outline the GPT quiz system tests from. Syncs to Google Calendar. Use when the user wants to study a topic on their own schedule.
user-invocable: true
---

# /custom-curriculum -- build a synthetic self-directed class

Arguments passed: `$ARGUMENTS` (may be empty, or a topic hint like "linear
algebra" / "organic chemistry basics").

This skill authors a complete course -- a week-by-week sequence **and a full
teaching outline for every chapter** -- for a class that doesn't exist
anywhere but here, registers it in the same local database real scraped
courses live in, and syncs it to Google Calendar in
exactly the format `academic-import` produces. The user **learns from real
readings linked on each banner** (found online in Step 1b). The GPT quiz
system (the `study-prompt-system` repo) reads each banner's TOPIC DETAIL
and gives 10 quiz-style questions over everything covered so far, so the
material sticks. GPT teaching mode was retired 2026-10-05. Read `CLAUDE.md` invariant 35 before your first run in a
session -- it's the authoritative carve-out this skill operates under.

**Working directory**: the `academic-sync` project at the repository root.
All CLI commands are `uv run academic-sync ...` via Bash.

**Live tools**: `WebSearch` / `WebFetch` in Step 1b, to find and verify real
readings. `mcp__claude_ai_Google_Calendar__*` in Step 4. Nothing here
touches D2L.

**What this skill produces**: `WEEKLY_READING` banners only, plus one
`chapter-topic-add` row per chapter, which `render` automatically pulls into
each banner, plus real reading/resource links. **No quizzes, exams,
homework, assignments, deadlines, or meetings -- ever** (user-directed
2026-09-25). Practice comes from the GPT quiz system's 10-question sets.

## Step 0: gather inputs

Ask directly, don't guess:

1. **Topic and academic level** -- e.g. "Linear algebra, intro/undergraduate".
2. **Course length in weeks** -- an integer. No default.
3. **Pacing tier** -- **Light** ~2-4 h/week · **Moderate** ~5-8 h/week ·
   **Intensive** ~9-14 h/week (rough ranges, say so).
4. **Start date** -- default to the upcoming Monday and say so plainly.

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
- **Objectives**: 6-12, in learning order, each building on the last. The
  GPT quiz system tests every one. Each one is one concrete,
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

## Step 1b: find real readings for every chapter (user-directed 2026-10-05)

A self-study course should be read from real material, the way a D2L
course is read from its real textbook. For each chapter, search the web
(`WebSearch`) for **official, openly available college course material**
on exactly that chapter's topic, in this order of preference:

1. **An open textbook chapter or section page**: OpenStax, LibreTexts,
   the Open Textbook Library, or a university press open edition.
2. **University course pages**: MIT OpenCourseWare lecture notes and
   readings, other universities' public course sites.
3. **Recorded lectures** from those same sources (MIT OCW video, a
   university's official channel).

For each find:
- **Verify it** with `WebFetch`: the page loads and covers this chapter's
  topic at this level. Never link a page you didn't open. Never link
  paywalled, pirated, or content-farm material.
- **The reading** becomes the chapter's `--reading-url` /
  `--reading-label`, e.g. `"OpenStax Calculus Vol 1 — 3.2 The Derivative
  as a Function"`.
- **Its real section headings** become `--section` values (the "Big
  topics" line). These come from the source, so they aren't authored
  content.
- **Lecture notes, videos, and problem sets** become that week's `--links`
  entries with a `kind` (`video`, `handout`, `other`).
- **Prefer one coherent primary text across the whole course** (e.g. one
  OpenStax book) so chapter readings follow one progression. Add a
  second source only where the primary doesn't cover a chapter.
- **If nothing reputable covers a chapter, leave its links empty.** Say
  so in Step 2 rather than linking something weak.

## Step 2: present for explicit approval (mandatory gate)

Show everything before any write: topic, level, weeks, pacing tier + hour
range, start date, the week-by-week plan (one line per week
with its date range and chapters), then **every chapter's full outline**
(title, ordered objectives, key terms) **with its reading link, section
headings, and resource links** from Step 1b.

The user's approval *is* what makes this content legitimate for this course
type (CLAUDE.md invariant 35). Don't skip it or proceed on an ambiguous or
partial yes. Apply requested edits and re-show the changed parts.

## Step 3: on approval, write to the database

1. Register the course once:
   ```
   uv run academic-sync course add \
     --code "<topic name>" --name "<topic name> — <academic level>" --term "<term>" \
     --start <start_date> --end <computed_end_date> --synthetic
   ```
   `--name` must carry the Step 0 academic level in plain words (e.g. `"Intro
   Statistics — introductory undergraduate"`). It renders into every event's
   header line, and it's the only place the GPT study system learns the
   course's level (its Academic Level inference reads that header). Keep
   `--code` the bare topic name, since it's the course's identifier in every
   event title. Never pass `--instructor`/`--instructor-contact` (a synthetic course has no
   CONTACT section). Run exactly once -- re-running `course add` without
   `--synthetic` would clear the flag.
2. Every chapter:
   ```
   uv run academic-sync chapter-topic-add --course <course_id> \
     --chapter "Chapter N" --title "<title>" \
     --vocabulary "<term>, <term>, ..." \
     --objective "<objective 1>" --objective "<objective 2>" ... \
     --section "<source section heading>" ... \
     --reading-url "<verified url>" --reading-label "<source — section>"
   ```
   Objectives in teaching order. **Never pass `--exhaustive`** -- that flag
   certifies a real platform's complete topic list and has no meaning here.
3. Every week:
   ```
   uv run academic-sync weekly-reading-add \
     --course <course_id> --week-start <date> --week-end <date> \
     --chapters "Chapter N: <title>; Chapter M: <title>" \
     --links '[{"label": "MIT OCW Lecture 5 video", "url": "...", "kind": "video"}]'
   ```
   Use the same chapter titles as step 2 so each banner's label matches its
   saved topic. All three commands are idempotent -- re-running corrects the
   same row, never duplicates.

## Step 4: render and push to Calendar

Reuse `academic-import`'s Step 5 flow exactly: for each
banner, `uv run academic-sync render <item_id> --json` (it auto-pulls the
saved chapter topics into READING and TOPIC DETAIL) → `mcp__claude_ai_Google_Calendar__
create_event` → `uv run academic-sync record-sync <item_id> --event-id <id>
--calendar-id <calendar_id>` right after each successful write. Batch
independent creates.

Spot-check one rendered banner before calling it done. It must start with
`SYNTHESIZED CURRICULUM`. Each chapter must appear under READING with its
"Big topics" line and reading link, and under TOPIC DETAIL with its key
terms and ordered objectives. A bare chapter line means a
`chapter-topic-add` label didn't match; use the same "Chapter N" number in
both commands.

## Step 5: close out

Tell the user: the course id, chapter and week counts, how many events were
synced, and that it appears under **Self-study courses** in the GPT quiz
chat.

## Rules that apply throughout (see CLAUDE.md invariant 35)

- Footprint: `WEEKLY_READING` banners + `chapter-topic-add` rows only. Never
  a quiz, exam, homework, assignment, deadline, meeting, or lab item.
- Never set `instructor`/`instructor_contact`; never pass `--exhaustive`.
- Never set `is_synthetic = True` on a course with any real scraped content,
  and never `False` on one this skill created.
- Every other CLAUDE.md invariant still applies -- no guests, no Meet links,
  idempotency by natural key, no dates outside the approved outline.
