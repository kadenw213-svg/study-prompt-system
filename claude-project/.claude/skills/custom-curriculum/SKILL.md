---
name: custom-curriculum
description: Build a fully synthetic, self-directed "class" on a topic the user describes -- no real D2L source -- using the same Course/AcademicItem model and Calendar-rendering pipeline a real scraped class uses, so it teaches the same way in the GPT study-prompt system. Use when the user wants to study a topic on their own schedule and have Calendar/GPT treat it like a real class.
user-invocable: true
---

# /custom-curriculum -- build a synthetic self-directed class

Arguments passed: `$ARGUMENTS` (may be empty, or a topic hint like "linear
algebra" / "organic chemistry basics").

This skill authors a week-by-week topic sequence for a class that doesn't
exist anywhere but here, registers it in the same local database real
scraped courses live in, and syncs it to Google Calendar in the exact same
format `academic-import` produces -- so the separate GPT study-prompt
system (the `study-prompt-system` repo's `boot.md` + `engine/`/`modes/`
rule files, one level above `claude-project/`) reads it and teaches from it exactly
like a real class. Read `CLAUDE.md` invariant 35 before your first run in a
session if you haven't already -- it's the authoritative carve-out this
whole skill operates under, and it does not relax any other invariant.

**Working directory**: this skill operates on the `academic-sync` project
at the repository root. All CLI commands below are `uv run academic-sync
...` run from that directory via Bash.

**Live tools this skill uses**: `mcp__claude_ai_Google_Calendar__*` for the
actual Calendar writes, in Step 4 only. Nothing in this skill ever touches
D2L or a browser -- there is no real source to scan.

**What this skill is not**: it is not a lighter version of `academic-import`.
It never extracts, never scrapes, never marks anything `--exhaustive`, and
never creates a deadline/meeting/exam item. Its entire output is
`WEEKLY_READING` banners -- the same lightweight, "no enrichment" form a
real class's weekly banner already falls back to when no `chapter-topic-add`
data exists for it (see `sync/calendar_payload.py::build_weekly_reading_
description`'s `this_week` fallback to the bare `_topic_line`). The GPT
study-prompt fills in real teaching depth at lesson time, using its own
knowledge, exactly the way it already handles any real class's thin
chapter -- see the study system's `engine/teach.md` ("at the real depth Calendar actually captured --
thin when the source is thin, never padded to look complete"). Authoring deep vocabulary/objective
lists here would be redundant with that and is explicitly out of scope.

## Step 0: gather inputs

Ask the user directly, don't guess any of these:

1. **Topic and academic level** -- free text, e.g. "Linear algebra,
   intro/undergraduate level" or "Organic chemistry, second course."
2. **Course length in weeks** -- an integer. No default.
3. **Pacing tier** -- offer exactly these three, framed honestly as rough
   ranges, not a precise measurement (there's no real source to measure
   authored content depth against):
   - **Light** -- roughly 2-4 hours/week
   - **Moderate** -- roughly 5-8 hours/week
   - **Intensive** -- roughly 9-14 hours/week
4. **Start date** -- if the user doesn't give one, default to the upcoming
   Monday (compute from today's date) and say so plainly rather than
   silently picking it.

## Step 1: author the week-by-week sequence (local, no writes yet)

Build a list of one short topic label per real calendar week, foundational
to advanced, calibrated to `weeks x pacing tier`. This is the one place
this skill asks real effort of you: get the *order* right for the subject
at the stated level -- prerequisite concepts before what depends on them,
the same structure any standard intro course for that subject already
follows. Depth is deliberately not your job here (see "What this skill is
not" above).

Rules:

- One `WEEKLY_READING` banner per real calendar week, never per chapter/
  topic. A topic that needs more than one week's worth of pacing simply
  spans multiple weekly banners -- mirror exactly how a real multi-week
  chapter already renders across several weeks in this system (e.g. "Chapter
  3: Polynomial and Rational Functions (9/16 - 10/4)" split across three
  weekly banners for a real course).
- Each week's label uses the same `"Chapter N: Topic; Chapter M: Topic"`
  shape `weekly-reading-add --chapters` already expects -- short, broad,
  landing in roughly the same character range a real class's unenriched
  banner renders at. Do not write vocabulary lists, objective lists, or
  multi-sentence paragraphs -- if you're writing more than a short topic
  phrase per chapter, you're doing the GPT study-prompt's job for it.
- Chapter/week granularity (how many weeks a given topic gets) is your own
  authorial pacing judgment against the tier's rough hour budget -- there's
  no formula, and it doesn't need to be exact.

## Step 2: present for explicit approval (mandatory gate)

Show the user the full proposed outline before writing anything to the
database or Calendar: topic, level, total weeks, pacing tier + hour range,
start date, and the complete week-by-week label sequence, one line per
week with its date range.

This gate matters *more* here than `academic-import`'s Step 4 plan/dry-run
step. There, the plan approves *what to sync* -- the content itself already
traces to something real the user could go re-check in D2L. Here there is
no such document: the user's approval of this outline *is* what makes the
content legitimate for this course type (CLAUDE.md invariant 35). Do not
skip or rush this step, and do not proceed on an ambiguous or partial yes.

## Step 3: on approval, write to the database

1. Register the course once:
   ```
   uv run academic-sync course add \
     --code "<topic name>" --name "<topic name>" --term "<term>" \
     --start <start_date> --end <computed_end_date> --synthetic
   ```
   Never pass `--instructor`/`--instructor-contact` -- a synthetic course
   has no CONTACT section by design (leaving these unset is what makes
   that automatic, see `sync/calendar_payload.py::_contact_line`). Run this
   exactly once per synthetic course -- re-running `course add` later
   without `--synthetic` would silently clear the flag (pre-existing
   behavior of this command for every field, not special to `is_synthetic`).
2. For every week in the sequence:
   ```
   uv run academic-sync weekly-reading-add \
     --course <course_id> --week-start <date> --week-end <date> \
     --chapters "<short topic label>"
   ```
   This is idempotent by `(course, week_start)` -- safe to re-run if a
   single week's wording needs correcting later.

## Step 4: render and push to Calendar

Reuse `academic-import`'s Step 5 flow exactly -- don't duplicate its logic
here. For each `WEEKLY_READING` item just created: `uv run academic-sync
render <item_id> --json`, map the output fields to
`mcp__claude_ai_Google_Calendar__create_event`, then `uv run academic-sync
record-sync <item_id> --event-id <id> --calendar-id <calendar_id>`
immediately after each successful write -- see academic-import's Step 5 for
the exact field-mapping table and the stale-event-id fallback (update
failing with "resource could not be found" -> fall back to create). Batch
several weeks per round of tool calls the same way, since these are all
independent creates with no cross-item ordering requirement.

Confirm every synced event actually shows the `SYNTHESIZED CURRICULUM` tag
at the top of its description (`sync/calendar_payload.py::
_synthesized_tag`) before telling the user it's done -- if it's missing,
`Course.is_synthetic` wasn't actually set and something upstream needs
fixing before continuing.

## Step 5: close out

Tell the user: the new course id, how many weeks were synced, and that
`academic-sync courses` / `academic-sync completeness` / `academic-sync
plan` all work normally against this course going forward since it lives
in the same table as their real courses (`completeness` will report
`COMPLETE` for it immediately -- that's expected, not a bug, see invariant
35).

## Rules that apply throughout (see CLAUDE.md invariant 35)

- Calendar footprint is `WEEKLY_READING` only -- never create a
  DEADLINE/MEETING/EXAM/LAB item for a synthetic course. There is no
  homework in this system; comprehension checking happens entirely inside
  the GPT study-prompt's adaptive study flow, outside this project.
- Never set `instructor`/`instructor_contact` on a synthetic course.
- Never call `chapter-topic-add` for a synthetic course.
- Never set `is_synthetic = True` on a course that has any real scraped
  content, and never set it `False` on a course this skill created.
- Every other CLAUDE.md invariant not specifically carved out by invariant
  35 still applies unchanged -- no guests, no Meet links, idempotency by
  natural key, no invented dates outside the approved outline.
