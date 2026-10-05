---
name: academic-sync
description: Recurring maintenance for a D2L/Brightspace course already fully scanned by /academic-import -- light-crawl re-scan (extending weekly banners), link refresh, and the Drive weakness-signal write. Use when the user asks to check for updates on an already-registered course, build the next weeks' banners, or refresh unlocked links. Daily grades/announcements/feedback are /daily-overview's job.
user-invocable: true
---

# /academic-sync -- recurring course maintenance

Arguments passed: `$ARGUMENTS` (may be empty, a term, a course code, or a
subcommand hint).

This skill is the standing weekly job for every course `/academic-import`
has already fully scanned at least once. It never handles a brand-new
course's first-time crawl -- see Step 0. Read `CLAUDE.md` before your first
run in a session if you haven't already; its invariants apply here exactly
as they do in `/academic-import`.

**Working directory**: `uv run academic-sync ...` from the repo root, same
as `/academic-import`.

**Live tools this skill uses directly**: Chrome browser control
(`claude-in-chrome`) for D2L/ALEKS navigation, `mcp__claude_ai_Google_
Calendar__*` for Calendar reads/writes, and -- for Step 4's weakness-signal
write (triggered from `/daily-overview`) -- Chrome browser control again, this time on sheets.google.com. The
Google Drive MCP connector (`mcp__claude_ai_Google_Drive__*`) can locate the
workbook (`search_files`) and read it (`read_file_content`), but has **no
tool that writes spreadsheet cell content** -- confirmed live, 2026-09-16
(`update_file` only changes a file's title/parent, and `create_file` only
creates brand-new files). Step 4 is therefore a real, live Sheets edit via
the browser, exactly like Step 1-3's D2L work -- not an API call.

## Step 0: orient

1. `uv run academic-sync courses` / `status` -- same as `/academic-import`
   Step 0.
2. For each course in scope, confirm it's actually eligible for this skill:
   `completeness --course <id>` should show synced items and an
   `Inspected:` list covering the mandatory areas. If a course has **no**
   prior sync history, this skill is the wrong one -- tell the user and
   point them at `/academic-import` instead. Don't attempt a light crawl on
   a course that's never had a real first-time scan.

## Step 1: light-crawl re-scan

Follow `docs/d2l_discovery.md#recurring-runs----light-crawl` exactly: always
re-open Announcements (in full) and the course Calendar for every course in
scope, extend Content/Modules only as far as the next not-yet-built
`WEEKLY_READING` week (`weekly-reading-add` + `chapter-topic-add` for it),
and resolve any gap a fresh Announcements/Calendar read surfaces using the
same "go look, don't just report" default as CLAUDE.md invariants 32/34.
Then run the same `render` -> `create_event`/`update_event` -> `record-sync`
flow `/academic-import` Step 5 uses for anything new or changed.

## Step 2: link refresh

Some items are correctly missing `reference_url`/`resource_url` not because
nobody looked, but because the assignment/quiz/dropbox folder was still
locked in D2L behind a release date at scan time (see `link_available_date`
capture, `docs/d2l_discovery.md#links`). This re-checks those items both
after their stated release date and a bit before it (in case D2L's stated
date was conservative) -- this is what keeps the calendar from quietly
going stale on every item that was locked at scan time.

1. `uv run academic-sync needs-link-refresh [--course <id>]` -- lists every
   item whose `link_available_date` falls within the last 14 days *or* the
   next 14 days (`--lookback-days`/`--lookahead-days` to widen either) but
   still has no real link. Prints "Nothing needs a link refresh right now"
   most weeks -- expected, not a failure.
2. For each listed item, navigate to the relevant D2L area and confirm
   whether it's unlocked yet. An "opens" (future) item still locked is not
   an error -- leave it, it's checked again next week. An unlocked item:
   find its real turn-in/content link (prefer the actual submission page).
3. Apply it: `uv run academic-sync render <item_id> --reference-url "..."
   [--reference-url-label "..."] --save` (or `--resource-url`). Saving a
   real URL is enough on its own -- the item stops showing up in
   `needs-link-refresh` once it has one.
4. Re-run `render <item_id>` (no `--save` needed) to get the updated
   payload, push it with `update_event` using the item's existing
   `SyncRecord.google_event_id`.
5. If still locked, leave it alone -- it resurfaces next run inside the
   lookback/lookahead window.

## Step 3: weekly grade diagnostic -- retired 2026-10-05

The weekly "<CODE> Previous Week Diagnostic" Calendar event is retired.
Its job now happens daily in `/daily-overview`: newly graded work with
verbatim feedback, missed deadlines with open/closed status, and the Red
triggers (zero, bombed major assessment, 2+ missing, steep drop) as "Needs
attention" lines. Don't create diagnostic events anymore.
`diagnostics.py`'s thresholds are reused by `digest.py`. Old
`diagnostic-*` commands stay for history only. See CLAUDE.md invariant 37
(amended).

## Step 4: Drive weakness signal (called by /daily-overview)

When `/daily-overview`'s `digest-ingest` prints a `signal_candidate` (a
major assessment newly under 60%), or another real red flag is tied to
identifiable chapter coverage (a bombed exam/quiz whose `module_label`/nesting names real
chapters, a real zero on a chapter-scoped item), write a weakness signal
into the **same** Google Drive workbook the GPT quiz system
(`study-prompt-system` repo, schema in `engine/memory.md`) already reads
for that class, so its next 10-question set weights that chapter as a
weak spot.

- Find the workbook (`search_files` for `fullText contains
  'studyPromptDriveMemory'`), open it in the browser at its real
  `docs.google.com/spreadsheets/d/<id>/edit` URL, and open the `index` tab
  to find the class's row and whether it already has a `signals_tab` value.
- **If this class has no signals tab yet**: insert a new column at the end
  of the `index` tab's header row named `signals_tab` (right-click the last
  column's letter -> Insert 1 column right -- the Name Box can't navigate
  to a column that doesn't exist yet, it errors "range exceeds sheet
  size"), set this class's row to `[class_slug]__signals`, then create a
  new sheet tab (the `+` button) and rename it (double-click the tab name)
  to that exact slug. Give it the header row `signal_id | chapter_key |
  chapter_label | reason | severity | source_week | created_at | status`.
- Append one row per affected chapter, leaving `chapter_key` blank -- the
  GPT session resolves it itself from `chapter_label` via the same
  canonicalization it already uses for exam coverage text; academic-sync
  only ever needs to write the real, human-readable chapter label(s) the
  item actually covered. `status = active`.
- **Typing into cells**: click the target cell (or the Name Box, e.g. type
  `P4` + `Return` to jump straight to it), then type each field's text and
  press the real `Tab` key (a separate `key` action) to move to the next
  column -- do **not** embed a `\t` character inside the typed text itself,
  it gets inserted as a literal space rather than moving to the next cell
  (confirmed live, 2026-09-16). A `\n`/`Return` at the end of a field does
  correctly commit-and-move-down. End a row with `Return` after its last
  column -- Sheets returns to column A of the next row automatically.
  Screenshot after each row to confirm it landed in the right cells before
  moving on; if anything looks wrong, `Ctrl+Z` immediately rather than
  typing over it.
- This is additive only -- never write into `quiz_tab`/`reviews_tab`
  directly (their `concept_key` is a session-invented token this skill can
  never produce) and never edit the prompt's existing tab/column
  structure.
- Not every RED needs this -- skip it when the cause isn't tied to
  identifiable chapter coverage (e.g. multiple small missing items across
  unrelated topics) rather than forcing a signal onto a guessed chapter.
- Close the browser tab when done, same tab-hygiene rule as any other live
  browser work this skill does.

## Step 5: weekly reminder event -- retired 2026-10-05

`/daily-overview` runs every morning on Windows Task Scheduler and does
link refresh and grade checking itself, so the recurring Sunday reminder
event is no longer needed. If it still exists on the calendar, ask the
user before deleting it. Never create a new one.

## After running

Print a short summary: what changed per course (light-crawl finds, banners
built, links refreshed), and remind the user
they can check `unresolved`/`plan`/`completeness` any time. Don't re-print
full item lists unless asked.

## Rules that apply throughout (see CLAUDE.md for the authoritative list)

Same rules as `/academic-import` -- never fabricate a date/nesting/
location, never add guests/Meet links, idempotent writes only. If
you're about to hand-write grade-classification logic, date math, or a
fingerprint instead of calling into `src/academic_sync/`, stop -- that
belongs in the Python package.
