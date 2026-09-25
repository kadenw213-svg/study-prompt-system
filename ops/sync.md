# Sync — currency check, Calendar load/refresh, discovery

All silent. Calendar is read-only.

## Currency check (runs when `today ≠ state.last_currency_check_date`)

1. **Tier 2 — full refresh** for each active class whose `last_calendar_sync_at` is > 7 days old, **or** whose cache has no `weekly_overview` covering today *while today is still inside that class's cached week range* (first `week_start` ≤ today ≤ last `week_end`) → Refresh Rule for that class. A class whose weeks have all ended isn't re-read just for that.
2. **Tier 1 — delta** for all other classes: **one** Calendar list call, today → today + 14 days, all events. For each event whose title starts with an active course code:
   - `calendar_event_id` not in the cache → parse and insert it (a new `calendar_cache` row, derived `content` rows, new concepts `Untested`);
   - already cached but the title/description changed → update the row (keys preserved);
   - a course code that isn't in `index` → Class Discovery for that code.
3. Recompute today's week for every class, plus `state.summaries` and `state.next_due` (real classes only).
4. One batched write: changed cache/content/quiz rows, `index.last_calendar_sync_at` for Tier-2 classes, `state.last_currency_check_date = today`, summaries, next_due. Read back.
5. **Redirect if anything changed** (a new/changed deadline, a new week, a new class):
   - Automatic → run the Scheduler now; switch if it picks another class (real classes only).
   - Single class / exam / homework → finish the current block, then one line: `New: CHE1011 Lab 4 due Tue — [A] to let Automatic rebalance.` If the new item is in the current class, fold it into routing (new week → start-of-scope reach-back).
   - Nothing changed → say nothing.

A failed Calendar call: keep the last good cache, don't update `last_currency_check_date`, and retry at the next block boundary. Mention it only if it fails twice: `I couldn't reach your calendar just now — studying from what's saved.`

## Calendar batching

- Search by course code + bounded date range per class, never the whole calendar unbounded.
- Prefer one broad list call over many single-event reads. Read each description once per pass.
- On failure or rate limit, retry with a narrower window, never the same large one.

## Load Procedure (first load of a class, or a Refresh)

1. Range = the term window (60 days back → 150 days forward), narrowed if the class's events cluster tighter.
2. List/search every event whose title starts with the course code in that range.
3. Classify: `<CODE> Weekly Overview` → `weekly_overview`; `CODE (Section N) Label — Topic` → `meeting`; `CODE Title Due` → `deadline`; an exam/midterm/final-type title → `exam`. If any of the class's events carry the `SYNTHESIZED CURRICULUM` tag → `index.synthetic = true`.
4. Parse each (`engine/memory.md` Parsing) → one `calendar_cache` row with its full `links` and `first_seen_on_calendar`.
5. Derive `content`: each overview's THIS WEEK → per-chapter chapter/concept rows (canonicalized against known chapters); each meeting's TOPIC/MODULE/DETAILS enriches its chapter or adds a lesson; exam `coverage_text` stays on its cache row.
6. Infer the Academic Level → `index.academic_level`.
7. Preserve Quiz/review state for every concept whose key still matches after canonicalization; new concepts → `Untested`.
8. Write the class tab group in one batch; read back the counts and representative rows.
9. Set `last_calendar_sync_at`, `chapter_count`, `concept_count`, and `status = active` only after validation.

Never ask the user to approve the structure. A chapter with no captured vocabulary/objectives stays a bare chapter.

## Refresh Rule (Tier 2)

Load Procedure, plus:
- Match against existing rows by stable key after canonicalization. Keep Quiz/review state only for reliable matches (ambiguous → new key, archive the old; never attach old confidence to a doubtful match).
- Keep `first_seen_on_calendar` on matched rows; set it only on new rows.
- Concepts gone from Calendar → `archived` (excluded from scope/coverage/mastery, history kept), and archive their active reviews.
- Recount chapters/concepts, re-infer the level, keep the teaching position if its lesson still exists (else the nearest valid lesson).
- Validate before the refreshed structure becomes authoritative. A mid-refresh failure → keep the old cache intact and report it concisely.

## Academic Level inference

Integer scale: 1–2 middle school · 3–4 high school · 5 entry college · 6–7 advanced undergrad · 8 master's · 9–10 doctoral/professional. Signals, in priority order: course code numbering; the real vocabulary and complexity in captured topics/DETAILS/coverage; explicit header language ("Introduction to…", "Advanced…", "for majors", "graduate"). Never term position. Default 5 only if there's no signal at all. Re-inferred only on a Load/Refresh.

## Class Discovery

1. Calendar search over 60 days back → 150 days forward, in as few bounded calls as practical.
2. Collect the leading course-code tokens common across events (`BIO1112`, `MAT 1340`). For an event whose description carries the `SYNTHESIZED CURRICULUM` tag, the code is the whole title before ` Weekly Overview` (e.g. `Intro Statistics`) — it may contain spaces — and the class is `synthetic`.
3. Per new code, open one representative event → the course name from its `CODE - Course Name` header.
4. Add one `index` row each (new `class_key`, slug, tab names, `status = active`) and create its tab group with headers. Never remove an existing row just because this window missed it.
5. Don't load full curriculum here; that happens on first study.

No events at all in the window → widen once to a year back and forward. Still none:
```markdown
## Select a Class

No classes were found on your calendar in the current term window.
```
