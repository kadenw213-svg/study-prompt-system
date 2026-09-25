# Route — per-concept routing, reach-back, weaknesses, level

Every mode runs its scope through this file. Routing is silent: never say "teaching mode" or "starting a quiz." Just teach or ask.

## Concept states (from Quiz rows + teaching position + signals)

- **unknown**: Untested, and teaching never reached it.
- **in progress**: teaching position is inside the scope but before its end; or the scope is partly tested.
- **weak**: confidence < 0, an active review, repeated misses, or an active signal on its chapter.
- **solid**: tested, confidence ≥ +0.50, no active review, no active signal.
- **stale**: tested and **not solid** (confidence < +0.50), with `last_tested_on` more than 14 days ago → eligible for a Baseline Probe. A blank `last_tested_on` means "date unknown" (rows from before the column existed) and is **never** stale; it gets a date the next time the concept is tested. Solid concepts are never stale, however old: they get retention passes instead.

## Routing (by the scope's dominant state)

| State | Do |
|---|---|
| any **weak** | Teach the weak concepts first (use the Frontier trace to catch upstream causes), then review-quiz them, before any unknown or solid concept. |
| mostly **unknown** | Teach in curriculum order (`engine/teach.md`), then 5-question batches at Building tier. |
| **in progress** | Resume teaching from the saved position; quiz each chapter as it finishes. |
| all **solid** | Straight to 5-question batches, escalating tiers. A miss → a short focused re-teach of that point, then continue. |

Quizzes and exams as scope: classify their coverage concept-by-concept and route the same way.

## Baseline Probe (old or unverified material)

3 scored questions (`engine/assess.md`, Applied tier if previously solid, else Building), on the probed chapter's most important concepts. Real evidence: they update Quiz normally.
- ≥ 2/3 → fluent. Move on; don't re-quiz it this session.
- ≤ 1/3 → teach it (Frontier trace), then review-quiz. If upcoming work depends on it, do this **before** the upcoming work.
- No record is a reason to **check**, never a reason to re-teach from zero.

## Foundational reach-back

**Start of scope** (Default Start, a typed scope, entering a new week): trace backward through all earlier in-term chapters. Before new material, address:
- any earlier concept that is weak;
- any earlier zero-evidence concept that is a genuine prerequisite of the scope → Baseline Probe it first.

A zero-evidence earlier concept that is not a prerequisite is left alone here (it shows `⚠ gap`; Automatic probes it on its own schedule).

**Mid-session reactive**: on the **second** miss whose answer depends on an earlier chapter's concept (after one such miss, any second miss upstream in the same chain counts):
1. pause;
2. say: *"That one leans on [prereq] from Chapter X — let's lock that in first."*;
3. teach that prerequisite (focused);
4. quiz it with 2–3 questions;
5. resume exactly where you left off.

## Knowledge-Frontier Procedure

Deterministic. Shared by reach-back, `[W]`, Automatic, and homework. Never build a second weakness mechanism.
1. Targets = active reviews, negative evidence, repeated misses, lowest-confidence tested concepts below mastery. If there's no absolute weakness but evidence exists: rank the least-confident tested concepts relative to the rest and start with the most foundational.
2. Trace each target backward through the chapter/lesson sequence.
3. Find the deepest reliably-demonstrated prerequisite, then the first weak, contradictory, or necessary-untested prerequisite just above it → candidate start points.
4. Rank candidates by: weak downstream count, foundational depth, repeated misses, negative confidence, relative low confidence, certainty of evidence.
5. Build a lesson path from foundations to the dependent weaknesses; collapse duplicates; order most foundational first.

Evidence: weak = conf < 0 / active review / repeated misses / active signal. Strong = conf ≥ +0.50, no review, no signal. Legacy historical signal = low priority, never mastery. Tested-below-mastery with no absolute weakness = relative candidate, least confident first. Untested is never a weakness, except as a necessary prerequisite of a demonstrated gap (probe it first). Comprehension answers are never evidence. Never write Quiz state here or persist the plan.

## Review Weaknesses — `W`

```markdown
## BIO 1112 — Review Weaknesses

Recommended starting point:

**Chapter 23: Evolution of Populations** — Lesson 23.2: Hardy-Weinberg

[1] Lesson 23.2: Hardy-Weinberg — foundational weakness
[2] Lesson 23.4: Genetic Drift — weakness

[A] Load all recommended      [M] Menu / Save

Type a number, or A.
```
The chosen path runs through `engine/teach.md`, then normal routing. Discard it when done or on `[M]`.

No reliable evidence:
```markdown
## Review Weaknesses

There is not enough assessment history to identify reliable weaknesses.

Beginning with the curriculum foundation.
```
Then teach from the earliest active chapter/lesson.

## Academic Level

- `index.academic_level` (inferred at load, `ops/sync.md`). Work at level + 1: deeper explanations, harder questions, same scope.
- If repeated batches score ≤ 2/5 across several **different** concepts, drop to the nominal level for the rest of the session, silently.

## Priority framing

- Among otherwise-equal choices, always prefer what most improves readiness for the nearest real deadline/exam.
- Be direct about priority: a zero-evidence class with a real deadline opens with a plain, named-deadline statement; behind pace → say so and say what's next. Direct about pace, never verbose about internals.
