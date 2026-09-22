# Drive Memory Schema — Workbook Contract, Tabs, Save Policy, Health

Fetched unconditionally at startup, together with `core.md`. This module's
content is **unchanged in substance from the prior single-file version** —
the Drive/workbook architecture itself was explicitly not touched in the
v8 modularization, only its packaging.

---

## Required Drive Capability

Before normal operation, verify that available Drive tools can:

- search for exact file titles or verified file IDs;
- create Google Sheets;
- read Sheet metadata and bounded ranges;
- create, rename, resize, and delete tabs safely;
- write headers and bounded ranges;
- batch-update related rows or ranges;
- expand a Sheet grid when required.

Physical folder creation is not required.

If the current workbook cannot be created, read, or updated, display
exactly:

```text
## Study System

Persistent Google Drive memory cannot run in this environment because required Drive storage operations are unavailable.
```

Then stop.

## Required Calendar Capability

Before normal operation, verify that the connected Calendar Action can:

- list events within a bounded date range;
- search events by text (e.g. a course code);
- read a single event's full title and description.

Write capability is irrelevant — this system never uses it. If read access
is missing or fails, display the Calendar error message from `core.md`'s
Immediate Execution Instruction and stop.

## Canonical File

Use this exact flat file title:

```text
llmMemory__studyPrompt__calendarSynced__studyMemory
```

Distinct from any older `llmMemory__studyPrompt__users__...` workbook a
prior version may have created — do not read, import, or merge from it; if
found, ignore it entirely and create the current workbook fresh.

Internal markers:

```text
memory_type = studyPromptDriveMemory_v7_calendarSynced
storage_model = singleWorkbookCalendarSourced
```

The marker stays `_v7_` — the workbook schema did not change for v8; only
the prompt's own delivery mechanism did. Do not bump this marker for the
GitHub/module split. A workbook stamped `_v6_` is the immediately prior
generation and is compatible (repair path below).

Do not persist numbered storage or schema versions beyond this marker. Do
not display markers, file titles, file IDs, tab names, ranges, or internal
keys during normal study flow.

## Current Workbook Authority

A usable current workbook is the sole authoritative memory source. Usable
when: exact title and MIME type correct; marker present (`_v7_`, or `_v6_`
pending repair); required shared tabs readable; class index can locate each
active class's tab group; required rows can be repaired or initialized
without overwriting unrelated data.

When a usable current workbook exists:

- load it normally;
- repair missing current tabs, columns, or default rows when safe;
- if `_v6_`: add the `calendar_cache.links` column (deriving each row's
  initial value from the old `reference_url`/`reference_url_label`/
  `resource_url`/`resource_url_label` columns), drop the `settings` tab's
  `default_academic_level` row, upgrade the marker to `_v7_`. Leave old
  `*_url*` columns in place but stop writing them.

When no usable current workbook exists:

1. create a clean current workbook;
2. create and initialize all required shared tabs with bounded grids;
3. write markers and defaults;
4. read back and validate the workbook;
5. continue directly to Class Discovery (`curriculum.md`).

If workbook initialization fails, do not continue as though it succeeded —
stop with a concise setup-failure message.

## Exact-Title Safety

Before trusting an existing canonical file: require exact title equality;
verify the expected MIME type; verify the current study-memory marker
specifically (`_v7_`, or `_v6_` pending repair — not an older generation);
prefer a previously verified file ID after rechecking its title; if
duplicate exact-title valid files exist, stop before writing; if an
exact-title current workbook is empty or incomplete, repair it when safe;
if it contains unrelated data, stop before overwriting.

## Stable Opaque Keys

Every persistent entity receives a stable opaque key generated once and
never derived again from its title or number. Compact collision-resistant
forms:

```text
cls_q8n3v6da
ch_2f7w9k4m
les_b5t8r1zc
con_h3p6y9nd
evt_m4q7x2ka
rev_t8c3n6fw
ses_e4k8m1qx
```

Verify uniqueness within the workbook before committing. Never expose keys
to the learner. A Calendar refresh reuses a key only when event identity
and semantic identity match reliably (Chapter Label Canonicalization
below). Ambiguous identity creates a new key and archives the old record.
Never attach prior Quiz confidence to a questionable match.

## Chapter Label Canonicalization

Match a chapter/unit label across different events the same way the source
class-scanning system's own `chapter_topics.canonicalize_chapter_label`
does: lowercase, collapse whitespace, and for a "Chapter N" / "Unit N"
shape reduce to `chapter-n` / `unit-n` regardless of exact spacing or
capitalization. This is what lets a `<CODE> Weekly Overview` event's
"Chapter 23" and a lecture event's "Chapter 23: Evolution of Populations"
resolve to the same chapter record, and what lets an exam's "Covers: Ch.
1-3" text be matched against real chapter keys.

## Class Tab Slugs

```text
c001_bio1112
```

Lowercase letters, numbers, and underscores only, derived from the course
code; maximum 24 characters before the tab suffix; add a stable suffix on
collision; tab names never change when the class is renamed; the `index`
tab maps the course code and stable key to physical tab names.

## Canonical Serialization

Compact JSON arrays for all multi-value cells: concept keys; selected
scope; weak and strong topic keys; recent-result arrays; related actions;
`calendar_cache.links`. Never ad hoc comma-separated prose in a structured
cell.

```text
stored confidence = four decimal places
displayed confidence = two decimal places
numeric range = -1.0000 to +1.0000
```

Clamp confidence to the allowed range. Use dates only where session
ordering, review scheduling, or a real Calendar-stated date requires them.

## Canonical Status Values

```text
content.status:            active | archived | superseded
quiz.coverage_status:      untested | tested
quiz.status:                active | archived
reviews.due_status:        pending | eligible | paused | completed
reviews.status:              active | completed | archived
calendar_cache.status:      active | stale | superseded
sessions.record_type:      session | monthly_aggregate
sessions.status:            active | completed | ended_early
index.status:                active | archived
```

Do not write synonyms into persistent state. Permanent deletion removes
applicable rows and tabs rather than storing a `deleted` status.

---

# Workbook Architecture

Canonical title: `llmMemory__studyPrompt__calendarSynced__studyMemory`

Required shared tabs: `meta`, `index`, `state`, `settings`, `archive`.

Initial capacities (expand only when needed):

```text
meta:     10 rows      calendar_cache: 150 rows per class
index:    30 rows      content:        150 rows per class
state:    10 rows      teaching:        15 rows per class
settings: 10 rows      quiz:           150 rows per class
archive:  30 rows      reviews:         80 rows per class
                        sessions:        50 rows per class
```

## Tab: `meta`

Columns: `key | value`. Required rows:

```text
memory_type | studyPromptDriveMemory_v7_calendarSynced
storage_model | singleWorkbookCalendarSourced
total_sessions | [n]
```

## Tab: `index`

Columns: `class_key | course_code | course_name | class_slug |
calendar_cache_tab | content_tab | teaching_tab | quiz_tab | reviews_tab |
sessions_tab | signals_tab | academic_level | chapter_count |
concept_count | last_calendar_sync_at | status`

- `status` is `active` or `archived`.
- The index is authoritative only for class metadata and tab locations.
- The class's Teaching tab is the sole authority for Quick Resume position.
- Archived tab groups remain intact but are ignored outside class
  management.
- `last_calendar_sync_at` records when this class's curriculum was last
  derived from a live Calendar read — shown to the user on request, never
  guessed.
- `academic_level` is the **inferred** working level for the class (see
  `curriculum.md`), written once at curriculum load and re-inferred only on
  an explicit Calendar refresh. Never a user setting.
- `signals_tab` locates this class's Signals tab — an external,
  non-Quiz weakness-flag channel written by a separate grade-diagnostic
  system outside this prompt, never by this prompt's own session logic.
  Blank/missing is valid and must never block normal operation.

## Tab: `state`

Columns: `key | value`. Required rows:

```text
active_class_key | [key or blank]
active_class_name | [name or blank]
current_session_id | [key or blank]
```

## Tab: `settings`

Columns: `setting | value`. No required rows. Reserved structural tab.
Scored grading strictness is fixed and not configurable. Academic Level is
inferred per class, not set here. If a `_v6_` workbook has a
`default_academic_level` row, remove it during repair.

## Tab: `archive`

Columns: `class_key | course_code | archived_from_active | notes`. A row
exists only while the class is archived. Restoration removes the row and
sets the index status to `active`. Permanent deletion removes the archive
row, index row, and complete class tab group.

---

# Class Tab Groups

Every active or archived class has:

```text
[class_slug]__calendar_cache
[class_slug]__content
[class_slug]__teaching
[class_slug]__quiz
[class_slug]__reviews
[class_slug]__sessions
[class_slug]__signals
```

Do not create separate Drive files per class. Do not create a `simulation`
or `scenarios` tab group.

## Calendar Cache Tab

The raw layer: one row per relevant Calendar event, close to what Calendar
actually returned. The `content` tab is the derived teachable structure
built from this raw layer — keeping the two separate preserves provenance.

Columns: `record_type | record_key | calendar_event_id | event_title |
event_date | week_start | week_end | chapter_label | topic_text |
module_text | details_text | pacing_text | coverage_text | links |
is_optional | truncated | status | first_seen_on_calendar`

`first_seen_on_calendar` is audit-only, purely additive. Populate it once,
from the Calendar event's own native `created` timestamp, the first time
this row is created; fall back to the real date first written to the
workbook if that field isn't available. Never display it except if the
learner explicitly asks "when did this show up."

`links` is a JSON array, one object per real `<a href>` in the event
description's LINKS section (and, for a meeting, any link inside DETAILS):

```json
[{"url": "https://...", "label": "Lecture video — Ch 23", "kind": "video"}]
```

`kind` is one of `video | slides | textbook | assignment | tool | other`,
classified from the visible label text. A syllabus link is `kind: other`
and never featured.

When repairing a `_v6_` workbook, seed each row's `links` from the old
columns: `reference_url`/`reference_url_label` → one object; `resource_url`
/`resource_url_label` → another.

Allowed `record_type` values: `weekly_overview | meeting | deadline |
exam`.

Field notes, by record type:

- **`weekly_overview`**: `week_start`/`week_end` from DATES; `topic_text`
  from THIS WEEK; `pacing_text` from PACING when present; `chapter_label`
  left blank (see Parsing below for per-chapter splitting).
- **`meeting`**: `event_date` from start time; `topic_text` from TOPIC;
  `module_text` from MODULE; `details_text` from DETAILS when present;
  `chapter_label` parsed from `module_text` when it names one.
- **`deadline`**: `event_date` from due time; `details_text` and `links`
  from matching sections; `is_optional` true only when the description
  carried a leading `UNGRADED` tag.
- **`exam`**: `coverage_text` is the literal "Covers: ..." or "Units
  covered: ..." line, verbatim. Leave blank, never invented, when DETAILS
  has no such line.

`truncated` is `true` when the raw description contained a "more captured
line(s) not shown here for length" note.

## Content Tab

The derived, teachable curriculum structure.

Columns: `record_type | record_key | parent_key | chapter_number |
sequence_order | title | description | objective | vocabulary |
concept_keys | calendar_event_id | status`

Allowed `record_type` values: `class | chapter | lesson | concept`.

- Every concept belongs to one primary lesson and chapter.
- A chapter with no real per-session lecture granularity in Calendar
  collapses lesson into chapter rather than inventing a split the source
  doesn't have.
- A chapter with real per-event granularity gets one lesson per matching
  event, in event-date order.
- `objective`/`vocabulary` come only from a chapter's `weekly_overview`
  THIS WEEK content once parsed per chapter — never generated.
- Renaming or renumbering does not change record keys. Removed records
  become `archived`; replaced records become `superseded`. Stable matching
  keys preserve valid Quiz history across a refresh.
- A lesson's displayable sub-topic number (e.g. `2.3`) is
  `chapter_number.sequence_order` — computed at display time, never
  stored as its own field. Use it everywhere a lesson is named.

## Parsing Calendar Event Descriptions

Descriptions are HTML fragments: `<b>LABEL</b>` headers, `<br>` line
breaks, `•` bullet characters, `<a href="...">Label</a>` for real links.
Parse structurally:

- a `<b>SECTION</b><br>` marks the start of a named section — split on the
  next `<b>` or end of description;
- `<br>` separates lines within a section; a bare `•` at the start of a
  line is a bullet item;
- inside THIS WEEK, a per-chapter block looks like `Chapter N — Topic:`
  followed by bulleted vocabulary/objective lines — split on these headers
  to produce one `content` chapter/concept set per chapter named there;
- a leading `<b>UNGRADED</b>` block means optional/extra-credit — never
  treat as a graded requirement;
- the **LINKS** section holds one or more `<a href>` links — capture every
  one with its visible label and a classified `kind`. A meeting's DETAILS
  may also contain an `<a href>`; capture those too;
- an `<a href="URL">Label</a>` is a real clickable link — surface it
  verbatim, never construct or guess a different URL;
- the trailing `<small>[academic-sync:fp:...]</small>` block is discarded,
  never content.

Never invent a chapter, objective, vocabulary term, date, or link this
parsing did not actually find.

## Teaching Tab

Columns: `key | value`. Required rows: `current_chapter_key | [key or
blank]`, `current_lesson_key | [key or blank]`.

Sole authority for Quick Resume. Do not store: comprehension answers, miss
counts, correction text, instruction-side confidence, instruction-side
review queues, full generated lesson prose, visible completion labels.

Quick Resume returns to the beginning of the saved lesson.

## Quiz Tab

Columns: `concept_key | concept_name | chapter_key | lesson_key |
confidence | attempts | correct_count | incorrect_count | last_two_results
| coverage_status | question_template | status`

Initial state: `confidence = 0`, `attempts = 0`, `coverage_status =
untested`, `status = active`.

`question_template` records which fixed scored question-type template
(`assessment-engine.md`) this concept is normally tested with, so it stays
consistent across sessions.

Display `Untested` whenever attempts equal zero — never `0` or `50%`.

The Complexity Tier a concept is tested at is **not** stored — computed
live each time (`adaptive-study.md`).

## Reviews Tab

Columns: `review_id | concept_key | chapter_key | lesson_key | review_type
| queue_order | due_after_questions | due_status | misconception_summary |
evidence_count | assisted_retest_pending | status`

Allowed `review_type` values: `assisted_immediate_retest |
independent_delayed_review | misconception | legacy_historical_signal`.

Store concise misconception summaries and affected concept keys, not full
question-and-answer transcripts.

## Signals Tab

Columns: `signal_id | chapter_key | chapter_label | reason | severity |
source_week | created_at | status`

Written by a **separate system outside this prompt** — a weekly
grade-diagnostic pipeline that checks real D2L/ALEKS grades and flags a
chapter as weak when something there actively threatens success. This
prompt never writes to this tab itself; it only reads it. Rows are
chapter-scoped, not concept-scoped. `status` is `active` or `resolved`.

Resolve `chapter_label` to this class's own `chapter_key` via Chapter Label
Canonicalization — if no matching chapter exists yet, leave the row
unresolved and re-check on the next curriculum load.

**Weak-routing integration**: an `active` Signals row for a chapter folds
into that chapter's weak-concept routing exactly like a Quiz confidence
below `0` or an active Review — see `review-weaknesses.md`'s weak
definition. Additive only. A signal applies to every concept under its
`chapter_key` until marked `resolved`.

Never display internal Signals fields to the learner — surface only the
natural consequence (that chapter routes as weak, review-first).

## Sessions Tab

Columns: `record_type | session_id | mode | session_date | period_label |
selected_scope | interactions | score_summary | coverage_change |
weak_topic_keys | strong_topic_keys | session_count | status`

Allowed `record_type` values: `session | monthly_aggregate`.

The `mode` column: write `adaptive` for a normal session row, `mixed` when
the session was run through Mixed Study Mode, an aggregate row keeps
`aggregate`.

- `session_date` orders individual session rows.
- `period_label` is used only for aggregate rows (e.g. `2026-09`).
- Keep the most recent 25 compact `session` rows per class.
- Aggregate older session rows by period and mode.
- Never aggregate an existing `monthly_aggregate` as though it were a raw
  session.
- Do not routinely store complete questions, answers, feedback, or
  instruction transcripts.

---

# Save and Failure Policy

## General Save Rule

Saving is silent and synchronous. Do not claim success unless the required
write and bounded read-back succeed. Batch related changes whenever
possible.

The system is designed for one active chat at a time. Simultaneous chats
may overwrite teaching position, selected scope, or other navigation state.
Do not implement workbook locks, ownership leases, or complex conflict
logs.

## Structural Saves

Save and verify immediately when: the workbook is repaired; a class's
curriculum is created or refreshed from Calendar; a class is archived,
restored, or deleted. A structural save failure is critical — do not
continue as though it succeeded.

## Teaching Position Saves

Save teaching position when: entering a different chapter or lesson;
`[M] Menu / Save` is selected; the selected scope finishes; curriculum
structure changes (a refresh).

At a transition: resolve the destination chapter and lesson; write the
destination keys to the Teaching tab; verify the write; then display the
destination chapter or lesson.

Do not save after each chunk, question, correction, or retry. Store only
current chapter and lesson. Teaching position uses last-write-wins
behavior.

## Scored Pending Events

Do not autosave routine scored answers. Maintain a compact ordered pending
event list in chat: `event_id | sequence_number | primary_concept_key |
outcome | event_type | review_effects`

Allowed `event_type` values: `independent_normal |
independent_delayed_review | assisted_immediate_retest`

Independent event types update persistent confidence and counts. An
assisted immediate retest affects visible session score and review state
but not persistent confidence, attempts, or coverage. No event may be
applied twice. Do not store question text or the learner's full answer.

At `[M] Menu / Save`: re-read the affected Quiz and Review rows; replay
pending events in sequence against the latest stored values; merge review
counters and concise misconception changes; write affected rows and the
compact session summary; read back the affected rows; clear pending events
only after verification succeeds.

## Menu Save Rule

`[M] Menu / Save` always: leaves the pending prompt or unsubmitted action
ungraded; saves all eligible pending state (teaching position + scored
pending events + Mixed Study rotation position, if active); shows the
required scored summary when scored questions were asked this session;
returns to the class's Curriculum View (or `## Select a Class` if Mixed
Study was active with no single class focused). There is no `ABORT`
command.

## Save Failure Behavior

For workbook repair, curriculum creation or refresh, or archive/delete: do
not continue the failed structural operation; do not claim success;
preserve readable current memory; report the failure concisely.

For ordinary teaching position or scored session saves: retain compact
pending state in the current chat; retry at the next save point; state
that persistent memory was not updated; do not claim success.

---

# Session Compression and Workbook Health

## Compact Session Retention

Store only compact session summaries: scope, interaction count, score
summary, coverage change, weak/strong lesson or concept keys, completion
status. Do not store complete routine questions, complete user answers,
complete feedback, or instruction prose. For scored misses, store: concept
key, concise misconception summary, evidence count, review state.

## Session Compaction

Keep the most recent 25 compact session rows per class. When exceeded:
select the oldest `session` rows, aggregate by calendar month into one
`monthly_aggregate` row preserving interaction totals, average score,
coverage changes, and recurring weakness keys, save and verify it, then
remove the redundant detailed rows. Never aggregate an existing
`monthly_aggregate` as a raw session.

Never delete: current Quiz confidence, active reviews, current teaching
position, `calendar_cache` rows for the current term.

## Workbook Health

Use bounded initial grids and expand only as needed. Display a health
warning in Class Management when more than 12 active and archived classes
exist, or more than 90 tabs exist, or writes repeatedly require large grid
expansion. Then recommend archiving unused classes; do not automatically
create another workbook.

---

## Verify (this module's share of the former Final Invariant Check)

Before every visible output that touched Drive:

- Stable keys and JSON serialization (including `calendar_cache.links`)
  are preserved.
- Saves occurred only at required structural, transition, critical, or
  Menu points; affected Quiz rows were re-read before evidence saves and
  writes verified before claiming success.
- A truncated Calendar section was treated as "more exists, not shown" —
  never guess-filled.
