# Memory — class tabs, parsing, load, save

## Keys, labels, values

- **Stable opaque keys**, generated once, never derived from a title or number, unique within the workbook, never shown: `cls_q8n3v6da`, `ch_2f7w9k4m`, `les_b5t8r1zc`, `con_h3p6y9nd`, `evt_m4q7x2ka`, `rev_t8c3n6fw`, `ses_e4k8m1qx`, `bnk_k2d7p4sv`.
- **Chapter Label Canonicalization**: lowercase, collapse whitespace; "Chapter N" / "Unit N" in any spacing or capitalization → `chapter-n` / `unit-n`. Used for every chapter match (weekly overview ↔ lecture ↔ exam coverage ↔ signals ↔ bank).
- **Class slug**: lowercase letters/digits/underscores from the course code, ≤24 chars, stable suffix on collision, never renamed (e.g. `c001_bio1112`). Tabs: `<slug>__calendar_cache`, `__content`, `__teaching`, `__quiz`, `__reviews`, `__sessions`, `__signals`, `__bank`. No other per-class tabs, no other Drive files.
- **Serialization**: compact JSON arrays/objects for every multi-value cell, never comma prose. Confidence is stored with 4 decimals and displayed with 2, clamped to `-1.0000…+1.0000`. Dates `YYYY-MM-DD`, used only where ordering, scheduling, or a real Calendar date needs them.
- **Status values** (no synonyms): `content.status: active|archived|superseded` · `quiz.coverage_status: untested|tested` · `quiz.status: active|archived` · `reviews.due_status: pending|eligible|paused|completed` · `reviews.status: active|completed|archived` · `calendar_cache.status: active|stale|superseded` · `sessions.record_type: session|monthly_aggregate` · `sessions.status: active|completed|ended_early` · `signals.status: active|resolved` · `bank.status: active|archived`.

## Class tabs

**calendar_cache** — the raw layer, one row per event: `record_type | record_key | calendar_event_id | event_title | event_date | week_start | week_end | chapter_label | topic_text | module_text | details_text | pacing_text | coverage_text | links | is_optional | truncated | status | first_seen_on_calendar`
- `record_type`: `weekly_overview | meeting | deadline | exam`.
- weekly_overview: `week_start`/`week_end` from DATES; `topic_text` from THIS WEEK; `pacing_text` from PACING; `chapter_label` blank.
- meeting: `event_date` = start; `topic_text` = TOPIC; `module_text` = MODULE; `details_text` = DETAILS; `chapter_label` parsed from MODULE when it names one.
- deadline: `event_date` = due; DETAILS + links; `is_optional = true` only with a leading UNGRADED tag.
- exam: `coverage_text` = the literal "Covers: …" / "Units covered: …" line, verbatim, else blank.
- `links`: JSON `[{"url","label","kind"}]`, `kind ∈ video|slides|textbook|assignment|tool|other` from the label. A syllabus link is `other`, never featured.
- `truncated = true` when the description has a "more captured line(s) not shown here for length" note.
- `first_seen_on_calendar`: set once from the event's `created` timestamp (else the first write date). Never overwritten. Shown only when asked "when did this show up."

**content** — the derived teachable structure: `record_type | record_key | parent_key | chapter_number | sequence_order | title | description | objective | vocabulary | concept_keys | calendar_event_id | status`
- `record_type`: `class | chapter | lesson | concept`. Each concept belongs to one lesson and one chapter.
- A chapter without per-event granularity collapses its lesson into the chapter; with it, one lesson per matching event in date order.
- `objective`/`vocabulary` only from THIS WEEK per-chapter content. Never generated; thin stays thin.
- Displayed lesson number = `chapter_number.sequence_order` (computed, never stored).
- Removed rows → `archived`; replaced rows → `superseded`; keys survive renames.

**teaching** (`key | value`): `current_chapter_key`, `current_lesson_key`, `last_studied_at`, `blocks_today`, `blocks_today_date`. Never stores comprehension answers, miss counts, corrections, instruction confidence, lesson prose, or completion labels. Last-write-wins. Quick Resume = start of the saved lesson.

**quiz**: `concept_key | concept_name | chapter_key | lesson_key | confidence | attempts | correct_count | incorrect_count | last_two_results | coverage_status | question_template | status | last_tested_on`
- New concept: `confidence 0, attempts 0, coverage_status untested, status active`, `last_tested_on` blank. Display `Untested` when attempts = 0, never `0` or `50%`.
- Complexity Tier is never stored.

**reviews**: `review_id | concept_key | chapter_key | lesson_key | review_type | queue_order | due_after_questions | due_status | misconception_summary | evidence_count | assisted_retest_pending | status`
- `review_type`: `assisted_immediate_retest | independent_delayed_review | misconception | legacy_historical_signal`. Concise misconception summaries only, never transcripts.

**signals** (read-only here — written by a separate grade-diagnostic system): `signal_id | chapter_key | chapter_label | reason | severity | source_week | created_at | status`
- Resolve `chapter_label` → `chapter_key` by canonicalization; if unmatched, leave it and retry on the next load. An `active` row makes every concept in that chapter **weak** until `resolved`. Blank or missing is valid. Never show its fields; show only the effect (review-first).

**sessions**: `record_type | session_id | mode | session_date | period_label | selected_scope | interactions | score_summary | coverage_change | weak_topic_keys | strong_topic_keys | session_count | status`
- `mode`: `class | auto | exam | homework`; aggregate rows use `aggregate`. `period_label` is for aggregates only (`2026-09`).
- Keep the newest 25 `session` rows. Beyond that, merge the oldest by calendar month into one `monthly_aggregate` (interaction totals, average score, coverage change, recurring weakness keys), verify, then delete the merged rows. Never re-aggregate an aggregate.

**bank** (question bank): `item_id | source | mode | concept_key | chapter_key | chapter_label | stem | answer_key | features | seen_count | first_seen | last_seen | status`
- `source`: `homework|quiz|exam|practice`. `mode`: `teach|check`. `features` JSON: `{"steps":n,"traps":[…],"format":"…","niche":bool}`. Rules for writing and using it: `modes/homework.md`.

Never delete: current Quiz confidence, active reviews, current teaching position, or current-term `calendar_cache` rows.

## Parsing Calendar descriptions

HTML fragments (a file-imported event may instead arrive as plain text: treat a line that is exactly an uppercase section name — `TOPIC`, `MODULE`, `DETAILS`, `THIS WEEK`, `PACING`, `LINKS`, `DATES`, `SYNTHESIZED CURRICULUM` — as that section header, and `Label (URL)` as a link). A `<b>SECTION</b><br>` starts a section, ending at the next `<b>` or the end. `<br>` = new line. A leading `•` = bullet. In THIS WEEK, `Chapter N — Topic:` + bullets = one chapter block, so split on these headers. Within a block: a `• Vocabulary: a, b, …` bullet → that chapter's `vocabulary`; every other bullet → one objective, **in the order given** (that order is the teaching order). When the chapter has no finer per-event granularity, each objective becomes one `concept` row (`sequence_order` = its position) and the Instruction Engine teaches them in that order. A leading `<b>UNGRADED</b>` = optional/extra credit, never a graded requirement. Capture every `<a href="URL">Label</a>` in LINKS (and in a meeting's DETAILS) verbatim; never construct or alter a URL. Discard the trailing `<small>[academic-sync:fp:…]</small>` (or bare `[academic-sync:fp:…]` in a file-imported event). Never invent anything parsing did not find.

## Load class (one batched read)

Read `<slug>__calendar_cache`, `__content`, `__teaching`, `__quiz`, `__reviews`, `__signals`, `__bank` for the class's active rows in one batched call. Hold them in context. Don't read `__sessions` unless compacting.
- No cache rows, or `index.last_calendar_sync_at` blank → run `ops/sync.md` Load Procedure first.
- Verify the cache is readable and structurally usable before relying on it.

## Pending events (in chat only)

Maintain an ordered list: `event_id | sequence_number | primary_concept_key | outcome | event_type | review_effects`. `event_type`: `independent_normal | independent_delayed_review | assisted_immediate_retest`. Also track pending bank rows. Don't autosave routine answers. Never store question text or full answers. No event is applied twice.

## Save (one batched write, then one read-back)

Run at: class switch, chapter/lesson change, scope end, `[M]`, curriculum structure change. Never after each chunk, question, correction, or retry. At a chapter/lesson transition: resolve the destination keys → write → verify → only then display the destination.
1. Re-read the affected `quiz`/`reviews` rows.
2. Replay pending events in order against the latest stored values (independent events update confidence/counts/`last_tested_on`; assisted retests change only review state). Merge review counters and misconception summaries.
3. Write in one batch: those rows; pending bank rows; `teaching` position + `last_studied_at` + `blocks_today`/`blocks_today_date`; one compact `sessions` row (scope, interactions, score, coverage change, weak/strong keys, status); `state.checkpoint`, `state.active_class_key`/`_name`, `state.auto_last_class_key` if Automatic; recomputed `state.summaries[class_key]` and `state.next_due`. Increment `meta.total_sessions` once per chat session.
4. Read back the written rows. Clear pending state only after verification.
- Failure: keep pending state in chat, retry at the next save point, and say `Progress couldn't be saved to Drive yet — I'll retry.` Never claim success.
- Structural saves (workbook repair, curriculum load/refresh, archive/restore/delete) must verify before continuing. On failure, stop that operation, keep the last good state, and report concisely.
- One active chat at a time. No locks; last write wins.

## Menu / Save — `M`

Leave the pending question/prompt ungraded; discard temporary miss counters and the selected scope; run Save; if scored questions were asked, show the Session Summary (`engine/assess.md`); return to the class's Curriculum View (from Automatic: `## Select a Class`).

## Summary line (for `state.summaries`)

Clauses joined with ` · `, each only when it applies, one line:
1. `Week of <week_start>` + ` · Ch <n>[–<m>]` from the `weekly_overview` covering today (omit both if none).
2. One of: `not started this week` / `teaching in progress` / `reviewing` / `solid this week` (teaching position + this week's chapter confidence).
3. `N weak` (confidence < 0, active review, or active signal).
4. `N reviews due` (review `eligible` or due).
5. Curriculum Time Remaining: count concepts below Quiz Mastery (conf < +0.80 or Untested) in this week's chapters **plus** earlier chapters with a gap or any weak concept; × 15 min; round **up** to 10 / 30 / 45 min, then whole hours above 45 min → `N Hours of curriculum Remain` / `N minutes of curriculum Remain`; omit if 0. A planning cue only; never gate anything on it.
6. `⚠ earlier gap` if any earlier-than-current-week chapter was never reached by teaching **and** is Untested.

Self-study course line: the same clauses (it has no deadlines, so priority never comes from due dates).

`state.next_due` = the soonest non-optional deadline/exam across active **real** classes, from today on: `CODE Title — Day` (weekday if within 7 days, else `Mon D`).
