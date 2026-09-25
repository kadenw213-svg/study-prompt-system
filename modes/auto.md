# Mode: Automatic

Studies across **every** `index.status = active` **real** class (archived excluded, no opt-out setting) and decides what to do next at every block. It never ends once caught up: it keeps rotating for retention. **Self-study (`synthetic`) courses are never picked, loaded, mentioned, or counted here** — they're studied only by selecting them directly.

## Enter

1. Study bundle loaded. `engine/memory.md` Load class for **every** active real class (one batched read per class; `ops/sync.md` Load Procedure for any class with no cache).
2. Run the Scheduler once for all classes and open with the plan: the reasoning, never a fixed schedule.
```markdown
## Automatic

BIO1112 — Ch 19 hasn't been checked in 18 days; quick check first.
MAT1340 — HW 2.3 due Fri; Ch 2.3 still weak.
CHE1011 — solid this week; will get retention passes.

Starting with BIO1112.

[K] Switch Class      [M] Menu / Save
```
The plan is computed live and never stored. `state.auto_last_class_key` only **lowers** that class's priority at entry; it is never a resume point.

## Scheduler (run fresh at every block boundary, after the Currency check)

Candidates come from all active real classes. Take the **first rule that yields work**:

1. **Deadline pressure**: a non-optional deadline/exam within 48 h whose coverage has weak or untested concepts → that class, that coverage (exam coverage via `modes/exam.md` rules).
2. **Old gaps**: earlier-than-current-week chapters that are Untested (never reached) or **stale** (`engine/route.md`), in any class. A class with **zero** Quiz evidence all term goes first. Then order by (a) prerequisite of this or next week's work, then (b) the oldest `last_tested_on`/week. → **Baseline Probe** (`engine/route.md`). Fluent → drop it from this rule for the session. Not fluent → teach + review-quiz it (a prerequisite goes before the dependent current work).
3. **Current work, balanced**: this week's unmastered chapters. Pick the class with the fewest `blocks_today` (count 0 when `blocks_today_date ≠ today`; +1 per finished block), ties → the oldest `last_studied_at`; within the class, use normal routing (weak → in progress → unknown).
4. **Retention**: the class with the oldest `last_studied_at` → one batch at Applied/Edge on solid concepts, preferring bank `niche`/repeat items.

**Guards**
- At most 3 consecutive blocks on one class unless rule 1 is still active for it. Then rule 1 is re-checked, and otherwise rules 2–4 run with that class excluded for one pick.
- Within a class, keep going mid-concept (don't switch in the middle of teaching one concept or an open review chain); switch only at a block boundary.
- Any scope lock (homework set, reach-back, typed scope, exam) ends by returning **here**, never by continuing into that class's next chapter.
- Tiers change live as state changes; re-announce the plan only when the overall picture changes enough to matter.

## Output

- Announce only real class changes, in one line with the real reason: `Switching to BIO1112 — Ch 19 hasn't been checked in 18 days.` Never narrate "staying on …".
- Batch complete block in Automatic:
```markdown
**Batch complete** — 4 / 5 this batch · session 12 / 15

[Enter] Continue      [W] Review a weak spot      [K] Switch Class      [M] Menu / Save
```
Enter = run the Scheduler. `[W]`, `[X]`, `[E]` act on the class that currently has the turn.

## Exit

- `[M]` → Menu Save → Select a Class. `[K]` → Save → Select a Class.
- A typed class/scope/exam → hand off to that card; when it completes, return here only if the user came from Automatic.

## Save

- At every class change: `engine/memory.md` Save for the class being left (`last_studied_at`, `blocks_today`), and `state.auto_last_class_key`.
- Per-class Teaching/Quiz/Reviews state goes through the normal Save path, the same as single-class. Sessions `mode = auto`.
