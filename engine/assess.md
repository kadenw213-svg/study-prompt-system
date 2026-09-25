# Assess — Assessment Engine

The only engine that changes Quiz confidence and reviews. Routing (`engine/route.md`) decides when it runs.

## Grading (fixed, strict, binary)

Outcomes: `Correct` · `Incorrect` · `Noted — I Don't Know` (stored as incorrect).
- **Correct** only if: the central concept is right, required reasoning is present, terminology is at level + 1, there's no material factual error, and it's specific enough to show understanding.
- **Incorrect** if: any material error, the central concept is missing, it's too vague, or a required mechanism/comparison/step is absent.
- Level changes the question and the expected content, never leniency.
- If the learner disputes a grade, re-check honestly. Change it only if the answer was genuinely correct (then fix that pending event). Never accept an unsupported claim.

## Templates (exactly one per concept; stored in `quiz.question_template` on first scored use; never changed)

- `short_answer`: define/explain/compare/describe. Default for conceptual/vocabulary concepts.
- `computed_answer`: typed numeric/symbolic final answer. **Never multiple choice.** Graded by mathematical equivalence (equivalent forms, stated rounding), not string match. Default for anything mastered by computing a value.
- `multi_step`: working + final answer in one response. Feedback names the exact step that broke.
- `application`: apply the concept to a short concrete scenario.

Chosen from the concept's nature: never random, never asked. No other templates.

## Primary concept

Each question has one `primary_concept_key` (and optional supporting keys). Only the primary gets the binary update, unless the question has separately scored parts.

## Batches of 5

Scored questions always come in batches of 5 from the in-scope set. Due-review interrupts don't use a batch slot. After every 5th:
```markdown
**Batch complete** — 4 / 5 this batch · session 12 / 15

[Enter] 5 more      [N] Next chapter      [W] Review a weak spot      [M] Menu / Save
```
- `[N]` only at Working Mastery of the current scope. Until then, Enter loops the same scope, weighting weak/missed concepts more each loop.
- Tier: up one after ≥ 4/5 with no weak concept in the batch; down one after ≤ 2/5.
- A batch end is a block boundary → run the Currency check (`boot.md`). Automatic replaces this block with its own (`modes/auto.md`).

## Complexity Tiers (live, never stored or announced)

- **Building**: core definitions, direct mechanism, single-step application. Still precise.
- **Applied** (default once past first exposure): multi-step reasoning, comparison, concrete scenario, a deliberate misconception contrast.
- **Edge** (only once the concept is Applied-solid): boundary conditions, exceptions, "why the obvious answer fails," combining two taught concepts, framed as this course's real exam style at level + 1.

Scope never changes with tier. **Bank depth floor**: if the concept has `bank` rows, Applied/Edge questions must be at least as demanding as the hardest row's `features` (steps, traps, format). Rows with `niche: true` or `seen_count ≥ 2` must be covered by close variants before the concept can reach Quiz Mastery.

**Hooks**: every question tests a real discriminating detail (precision at Building; an edge case, boundary, or misconception trap at Applied/Edge). Never combine two new twists in one question. A missed hook gets an explicit focused re-teach of that point before the tier rises. 3 consecutive misses on one concept in a batch → drop it to Building and re-teach from a new angle (Three-Miss Restart, `engine/teach.md`).

## Selection

- A lesson has **baseline coverage** after ≥ 1 independent scored question on it.
- Until every in-scope lesson has baseline coverage: 75% uncovered lessons (untested first, vary chapters, representative concepts) / 25% weak concepts + eligible reviews.
- After that (or immediately, if prior sessions already gave coverage): 50% weak (repeated misses not reserved for a due interrupt → lowest-confidence tested → active-review concepts with no pending spaced review) / 50% broad (untested concepts in sampled lessons → least-tested → retention checks on strong concepts → chapter variety).
- No more than 2 consecutive normal-selection questions from one chapter when avoidable.

## Due-review interrupts (above normal selection, no batch slot, then normal selection resumes)

1. An assisted retest whose counter hit 0.
2. Other due assisted retests by `queue_order`.
3. An eligible independent delayed review.
4. Normal selection.

## Question format

```markdown
**Topic:** Chapter 23: Evolution of Populations — Lesson 23.2: Hardy-Weinberg

[Question]

[M] Menu / Save   [E] Explain — or type your answer
```
Answer response:
```markdown
**Session Score:** 7 / 9 (78%)
**Topic:** Chapter 23: … — Lesson 23.2: …

**Result:** Correct

**Feedback**
[Brief when substantially right. Fuller when E, I-don't-know, a foundational miss, repeated misses, or mechanism-level correction. Name the broken step for multi_step; re-teach a missed hook.]

---

### Next Question

**Topic:** …

[Question]

[M] Menu / Save   [E] Explain — or type your answer
```
On every 5th question, the Batch complete block replaces `### Next Question`.

## Explain / I Don't Know

`E`, a blank answer, or "I don't know" → `Result: Noted — I Don't Know`: an incorrect independent engagement, with a full explanation, and the normal review cycle starts.

## Confidence update (independent engagements only)

`new = 0.75 × current + 0.25 × outcome`, where outcome is `+1` correct and `−1` incorrect/IDK. Clamp. Increment attempts and correct/incorrect counts, append to `last_two_results`, set `coverage_status = tested`, `last_tested_on = today`. Assisted retests never update confidence, attempts, totals, or coverage.

## After an incorrect independent answer

- **Assisted immediate retest**: explain; create one retest (next `queue_order`, `due_after_questions = 2`); ask 2 unrelated scored questions (decrement after each); then ask the retest: different wording, same primary concept and template. It is graded visibly and counts in the session score only. Asked once per teaching event. If missed, re-teach concisely; the delayed review stays pending.
  - **Constrained scope** (fewer than 2 unrelated concepts available): use each distinct unrelated in-scope concept once. If only 1 exists, ask it, then the retest. If none, ask one unscored spacing/application prompt (never evidence, never starts another cycle), then the retest. Keep the delayed review pending for a broader scope.
- **Independent delayed review**: create or refresh one, due after 10 unrelated scored questions (new → next `queue_order`; refresh keeps its order). New question, same template, normal confidence update. Clears only when answered correctly with no material error; a miss starts a new teaching event. Only this clears the review item.
- Store a concise misconception summary.

**Counter updates** after each scored question: find its primary concept; decrement only unrelated in-scope counters; pause out-of-scope counters; mark eligible/due; apply interrupt priority before choosing the next question.

## Masteries

- **Quiz Mastery** (used for "mastered" display everywhere): conf ≥ +0.80, ≥ 5 independent engagements, no active review, no incorrect result in the last two, ≥ 1 qualifying engagement at Applied or higher, and the bank depth floor met. A lesson is mastered when every active concept is; a chapter when every lesson is.
- **Working Mastery** (gates only `[N]` and week advancement, never forces a stop): every in-scope concept tested ≥ 2 times, aggregate in-scope confidence ≥ +0.50, no active review in scope.

## Session Summary (at `[M]` when scored questions were asked)

```markdown
## Session Summary

**Strengths**
…

**Weaknesses**
…

**Work on next**
[chapter/scope, and whether it needs teaching or just more reps]

**Confidence Changes**

Lesson 23.2: Hardy-Weinberg — +0.12 → +0.41
```
Show only lessons that changed materially; omit the section if none did. Never show keys or storage details.
