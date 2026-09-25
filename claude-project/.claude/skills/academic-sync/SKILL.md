---
name: academic-sync
description: Recurring weekly maintenance for a D2L/Brightspace course already fully scanned by /academic-import -- light-crawl re-scan, link refresh, and the weekly Red/Yellow/Green grade diagnostic (one "<CODE> Previous Week Diagnostic" Calendar event per course). Use when the user asks to check for updates on an already-registered course, refresh unlocked links, check their grades, or run their weekly academic status check.
user-invocable: true
---

# /academic-sync -- recurring weekly maintenance

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
write -- Chrome browser control again, this time on sheets.google.com. The
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

## Step 3: weekly grade diagnostic

Produces one Calendar event **per course** every week -- **"<CODE> Previous
Week Diagnostic"** -- each independently colored Red/Yellow/Green
(user-directed 2026-09-17, superseding the original single cross-course
banner design). One event per course means each can carry full detail
without one very long list burying a struggling class among fine ones, and
each course's own color makes a gap visible at a glance on the calendar
itself, without needing to open anything. See
`docs/d2l_discovery.md#weekly-grade-diagnostic-crawl` for the full crawl
procedure this step follows; this is the sequence to run it:

1. **Crawl.** Read `docs/d2l_discovery.md#weekly-grade-diagnostic-crawl`
   in full before starting -- it has the concrete, hard-won mechanics
   below; this is just the summary. For each course, open D2L's
   **Grades** tool (the authoritative score record -- not just Content)
   and, for external courseware (ALEKS etc.), its own Gradebook
   independently, even if Grades already shows some real scores for that
   course (same "full view, not the dashboard" rule as CLAUDE.md
   invariant 23).
   - **A blank Grades cell is ambiguous** ("not yet graded" vs. "never
     submitted") -- confirm real missing-ness on the Assignments/Dropbox
     completion-status page's `Completion Status` column instead of
     inferring it from an absent score.
   - **Feedback location depends on item type**: Dropbox items show it via
     `Evaluation Status` -> `View Feedback` on that same completion page;
     rubric-graded items often expand inline on the Grades page itself via
     `View Graded Rubric`; quiz-type items via `View Quiz Attempts`; a
     scanned "Show Work" exam may only have inline PDF annotations -- note
     that real feedback exists there and point the user at D2L directly
     rather than transcribing handwriting. For every item graded or newly
     missing since last week's diagnostic, capture score/percent, and if
     under 90%, capture the literal instructor text if present -- never
     invent feedback that isn't there.
   - **If a live due/availability date conflicts with what's stored
     locally, the live page wins** -- flag it and correct it through the
     real `extract` pipeline (never hand-edit `.date`), don't just note
     the conflict and move on.
   - Re-open Announcements for the week (already required by Step 1) and
     note anything new for the highlights section.
2. **Record snapshots**, one call per item observed:
   ```
   uv run academic-sync grade-snapshot-add --course <id> --title "..." \
     --week-start YYYY-MM-DD [--score-percent N] [--missing] \
     [--feedback "..."] --source-type <d2l_quizzes|d2l_dropbox|external_courseware|...>
   ```
   and one call per course for the overall grade:
   ```
   uv run academic-sync course-grade-snapshot-add --course <id> \
     --week-start YYYY-MM-DD --overall-percent N [--letter-grade "B+"]
   ```
   If a gradebook row doesn't clearly match a local `AcademicItem`, still
   record the snapshot against the course (no `--item-id`) rather than
   dropping it.
3. **Compute status:**
   ```
   uv run academic-sync diagnostic-compute --week-start <monday>
   ```
   Prints each course's Red/Yellow/Green status and the data needed to
   build the description below (this week's snapshots, the prior week's
   overall grade for the week-over-week change, missing-item count,
   upcoming big deadlines within 21 days pulled from existing
   `AcademicItem`s of type `exam`/`final_exam`/`project`/`paper`/
   `presentation`/`lab_practical`/`presentation`).
4. **Build and push each course's own event, one at a time.** Call
   `diagnostic-render` (see below) rather than hand-typing this shape --
   same "don't reconstruct the template by hand" reasoning as `render` for
   a normal item, and **copy its printed `description` output verbatim
   into `create_event`/`update_event` -- don't retype or re-escape it.**
   HTML tags must go in as literal `<b>`/`<br>` characters, never as
   `&lt;b&gt;`/`&lt;br&gt;` entities -- a real incident, 2026-09-16, sent
   escaped entities by hand and Calendar displayed the literal escaped
   text instead of rendering it. User-directed 2026-09-17 layout, per
   course:
   - Line 1 (bold): the course code alone, e.g. `BIO1112` -- **no status
     word in the text**; the event's own `colorId` (step 5) carries
     Red/Yellow/Green now that each course has its own event.
   - Line 2 (bold): the grade change, e.g. `82.4% B- → 85.1% B` (or just
     the current grade if there's no prior-week snapshot yet).
   - A blank line, then **one block per assignment**, each separated from
     the next by a blank line: one **bold** `Name - score` line (or `Name -
     Missing`), then -- only when it applies -- a second, unbolded line
     with the real instructor feedback (if any) blended with your own
     suggested corrective action, or your own assessment alone if no
     feedback exists. An item ≥90% with no real instructor notes stops at
     the bold `Name - score` line; don't add a second line with nothing to
     say.
   - Then, each only when there's something real to put in it: announcement
     highlights and the upcoming-big-deadline lookahead (next 3 weeks).
   - **At the very bottom, one "Plan" section** that opens with any missed
     -deadline facts as bullets (state plainly whether the deadline's
     submission window is still open or already closed -- a real, sourced
     fact, not generated) immediately followed by your numbered corrective
     plan for that course specifically. A missed deadline is never its own
     separate section -- it's the lead-in to the plan that addresses it.
   The scores, feedback, and missed-deadline open/closed status must trace
   to real D2L/ALEKS content, same evidentiary bar as everywhere else in
   this project -- the plan/commentary itself is explicitly Claude's own
   generated recommendation, not sourced fact.
5. **Create/update this course's event.** All-day, dated the Monday of the
   week just completed, titled `"<CODE> Previous Week Diagnostic"`,
   `colorId` from this course's own status
   (`diagnostic_color_red`/`_yellow`/`_green` preferences -- defaults
   Tomato/`11`, Banana/`5`, Sage/`2`), no guests, no Meet link. Check for an
   existing event first via the fingerprint tag (same
   `list_events(fullText=...)` backstop `/academic-import` Step 5 uses) --
   `diagnostic-render` prints the fingerprint and any existing
   `google_event_id`. Create or update accordingly, then:
   ```
   uv run academic-sync diagnostic-record-sync --course <id> \
     --week-start <monday> --event-id <id> --status <RED|YELLOW|GREEN>
   ```
   Repeat steps 4-5 for every course -- each is its own independent
   `diagnostic-render` call and its own Calendar event, not a batch.

## Step 4: Drive weakness signal (only on a RED course tied to real chapter coverage)

When Step 3 flags a course RED for a reason tied to identifiable chapter
coverage (a bombed exam/quiz whose `module_label`/nesting names real
chapters, a real zero on a chapter-scoped item), write a weakness signal
into the **same** Google Drive workbook the GPT study system
(`study-prompt-system` repo, schema in `engine/memory.md`) already reads
for that class, so the next
GPT session already shows it as a weak spot needing review.

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

## Step 5: weekly trigger reminder (set up once per course, not every run)

The recurring Sunday reminder event (`RRULE:FREQ=WEEKLY;BYDAY=SU`) created
the first time a course reaches this skill covers **both** link refresh and
the grade diagnostic in one weekly nudge -- there is only ever one such
event per user, not one per course. If it doesn't exist yet, create it via
`create_event` (Sunday evening, a distinct `calendar_color_id` from normal
academic events, no guests, no Meet link) with a description telling the
user to invoke `/academic-sync` for the coming week. If it already exists
(from before this skill existed, it may still say "run link refresh" or
reference `/academic-import`), update its description text via
`update_event` to mention both jobs and the correct skill name -- don't
create a second event and don't change its recurrence rule or color.

## After running

Print a short summary: what changed per course (light-crawl finds, links
refreshed, this week's diagnostic status per course), and remind the user
they can check `unresolved`/`plan`/`completeness` any time. Don't re-print
full item lists unless asked.

## Rules that apply throughout (see CLAUDE.md for the authoritative list)

Same rules as `/academic-import` -- never fabricate a date/nesting/
location, never add guests/Meet links, idempotent writes only. For the
grade diagnostic specifically: scores and quoted instructor feedback must
trace to real D2L/ALEKS content; the corrective plan/recommendation text is
explicitly Claude's own generated advice, which is not a relaxation of that
rule (CLAUDE.md invariant 22 governs curriculum *content*, not advice). If
you're about to hand-write grade-classification logic, date math, or a
fingerprint instead of calling into `src/academic_sync/`, stop -- that
belongs in the Python package.
