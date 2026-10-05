# Memory — class tabs, parsing, load, save

## Keys, labels, values

- **Stable opaque keys**, generated once, never derived from a title or number, unique within the workbook, never shown: `cls_q8n3v6da`, `ch_2f7w9k4m`, `con_h3p6y9nd`, `evt_m4q7x2ka`, `rev_t8c3n6fw`, `ses_e4k8m1qx`.
- **Chapter Label Canonicalization**: lowercase, collapse whitespace; "Chapter N" / "Unit N" in any spacing or capitalization → `chapter-n` / `unit-n`. Used for every chapter match (weekly overview ↔ meeting ↔ exam coverage ↔ signals ↔ links).
- **Class slug**: lowercase letters/digits/underscores from the course code, ≤24 chars, stable suffix on collision, never renamed (e.g. `c001_bio1112`). Tabs used: `<slug>__calendar_cache`, `__content`, `__quiz`, `__reviews`, `__sessions`, `__signals`. Older `__teaching` / `__bank` tabs may exist: never read, write, or delete them.
- **Serialization**: compact JSON for every multi-value cell. Confidence stored with 4 decimals, clamped to `-1.0000…+1.0000`. Dates `YYYY-MM-DD`.
- **Status values**: `content.status: active|archived|superseded` · `quiz.coverage_status: untested|tested` · `quiz.status: active|archived` · `reviews.status: active|completed|archived` · `calendar_cache.status: active|stale|superseded` · `sessions.record_type: session|monthly_aggregate` · `signals.status: active|resolved`.

## Class tabs

**calendar_cache** — one row per event: `record_type | record_key | calendar_event_id | event_title | event_date | week_start | week_end | chapter_label | topic_text | module_text | details_text | pacing_text | coverage_text | links | is_optional | truncated | status | first_seen_on_calendar`
- `record_type`: `weekly_overview | meeting | deadline | exam`.
- weekly_overview: `week_start`/`week_end` from DATES; `topic_text` = the READING section's chapter headers + Big topics (or legacy THIS WEEK); `pacing_text` from PACING; `chapter_label` blank.
- meeting: `event_date` = start; `topic_text` = TOPIC; `module_text` = MODULE; `details_text` = DETAILS; `chapter_label` from MODULE when it names one.
- deadline: `event_date` = due; TOPIC/MODULE; `chapter_label` from MODULE (or TOPIC); `is_optional = true` only with a leading UNGRADED tag.
- exam: `coverage_text` = the literal "Covers: …" / "Units covered: …" line, verbatim, else blank.
- `links`: JSON `[{"url","label","kind","chapter"}]`. `kind ∈ textbook|slides|video|handout|platform|assignment|submit|other`. `chapter` = the canonical chapter a READING link sits under (blank otherwise). A syllabus link is `other`, never shown.
- `truncated = true` when TOPIC DETAIL ends with a "more captured line(s) not shown here for length" note (the EXPAND rule in `engine/quiz.md` then applies).

**content** — the quizzable structure: `record_type | record_key | parent_key | chapter_number | sequence_order | title | description | objective | vocabulary | concept_keys | calendar_event_id | status`
- `record_type`: `class | chapter | lesson | concept`. Lessons are optional; a concept belongs to one chapter.
- Concepts come from TOPIC DETAIL objectives (one concept per objective, in order), plus section headings created on first use by the EXPAND rule. Vocabulary from the `• Vocabulary:` bullet.

**quiz**: `concept_key | concept_name | chapter_key | lesson_key | confidence | attempts | correct_count | incorrect_count | last_two_results | coverage_status | question_template | status | last_tested_on | formats_seen`
- New concept: `confidence 0, attempts 0, coverage_status untested, status active`, `last_tested_on` blank, `formats_seen []`. Blank `last_tested_on` means "date unknown". `question_template` is legacy: leave as is.

**reviews**: `review_id | concept_key | chapter_key | lesson_key | review_type | queue_order | due_after_questions | due_status | misconception_summary | evidence_count | assisted_retest_pending | status`
- New rows: `review_type = retest`, `due_status = pending`, a one-line misconception summary. Older review types stay; treat any `active` row as "weak until re-proven".

**signals** (read-only — written by the class-sync system from real grades): `signal_id | chapter_key | chapter_label | reason | severity | source_week | created_at | status`
- Resolve `chapter_label` → chapter by canonicalization. An `active` row makes that chapter's concepts **weak** until `resolved`. Never show its fields.

**sessions**: `record_type | session_id | mode | session_date | period_label | selected_scope | interactions | score_summary | coverage_change | weak_topic_keys | strong_topic_keys | session_count | status`
- New rows use `mode = quiz`. Keep the newest 25 `session` rows; merge older ones by month into one `monthly_aggregate`, verify, then delete the merged rows.

Never delete current quiz confidence, active reviews, or current-term `calendar_cache` rows.

## Parsing Calendar descriptions

HTML fragments. `<b>SECTION</b><br>` starts a section, ending at the next top-level `<b>SECTION</b>` or the end. `<br>` = new line. A leading `•` = bullet. Discard the trailing `<small>[academic-sync:fp:…]</small>`. Never invent anything parsing did not find; never construct or alter a URL.

**Weekly Overview (current layout):**
- **READING**: blocks separated by blank lines. Each block starts with a bold chapter header `Chapter N — Title`, then optionally `Big topics: a · b · c` (real section headings, kept verbatim), then optionally `→ <a href="URL">Label</a>`, a `textbook` link tied to that chapter. A trailing block of `→` links with no header = textbook links for the whole week.
- **SLIDES &amp; RESOURCES**: one `<a>` per line. Set `kind` from the label (slides / video / handout / platform-name / other).
- **PACING**: verbatim.
- **TOPIC DETAIL**: per chapter, `<b>Chapter N — Title:</b>` then bullets. `• Vocabulary: …` → vocabulary; every other bullet → one objective, in order.
- **DATES**: the week range.
- A leading `SYNTHESIZED CURRICULUM` tag → self-study course.

**Legacy overview layout** (older events, until re-rendered): **THIS WEEK** holds the per-chapter bullets (parse like TOPIC DETAIL); **LINKS** holds all links (a label containing "Textbook"/"Reading" → `textbook`).

**Meetings / deadlines / exams**: TOPIC, MODULE, DETAILS, LINKS. In LINKS, a "Submit Work" label → `submit`. A leading `<b>UNGRADED</b>` = optional.

## Load class (one batched read)

Read `<slug>__calendar_cache`, `__content`, `__quiz`, `__reviews`, `__signals` active rows in one batched call. Don't read `__sessions` unless compacting.
- No cache rows, or `index.last_calendar_sync_at` blank → run `ops/sync.md` Load Procedure first.

## Save (one batched write, then one read-back) — after every graded set and at `K`/`X`

1. Re-read the affected `quiz`/`reviews` rows.
2. Apply the set's updates (`engine/quiz.md` Updates) against the latest stored values. New concepts → new `content` + `quiz` rows.
3. Write in one batch: those rows; one compact `sessions` row per set (scope, 10, score, weak/strong keys); `state.active_class_key`/`_name`; recomputed `state.summaries[class_key]`. Increment `meta.total_sessions` once per chat.
4. Read back. On failure keep the updates in chat, retry at the next save, and say `Progress couldn't be saved to Drive yet — I'll retry.` Never claim success.

## Summary line (for `state.summaries`)

Clauses joined with ` · `, each only when it applies: `Covered: Ch <first>–<last>` · `N weak` (active review, confidence < 0, or active signal) · `last quiz S/10`.
