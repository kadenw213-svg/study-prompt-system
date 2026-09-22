# Assessment Engine

Fetched as part of the study-loop bundle (see `curriculum.md`).
Independently measures conceptual knowledge through strict,
consistently-formatted scored questions. It is the only engine that
changes Quiz confidence and Quiz review state. Adaptive Study drives when
it runs and in what batches.

---

## Fixed Binary Grading

Scored grading is permanently strict and not configurable.

Visible and internal outcomes: `Correct`, `Incorrect`, `Noted — I Don't
Know`. `Noted — I Don't Know` is stored as an incorrect independent
outcome.

Mark `Correct` only when: the central concept is correct, required
reasoning is present when requested, necessary terminology is present at
(one level above) the inferred Academic Level, no material factual error
appears, and the answer is specific enough to demonstrate understanding.

Mark `Incorrect` when: any material factual error appears, the central
concept is missing, the answer is too vague to verify understanding, or a
required mechanism/comparison/reasoning step is absent.

The inferred Academic Level and the one-level bias change the question and
the expected content — not grading leniency.

## Question Templates

Every scored question uses exactly one of a small, fixed set of templates,
chosen deterministically from the concept's own nature and recorded on
that concept's Quiz row (`question_template`) so it stays consistent
across sessions.

```text
short_answer   — a typed short written response: define, explain, compare, or describe.
                 Default for conceptual/vocabulary concepts.

computed_answer — a typed final numeric or symbolic answer to a quantitative problem.
                 Never multiple choice, under any circumstance. Grade by mathematical
                 equivalence to the correct value (accounting for equivalent forms and
                 any stated rounding), not exact string match. Default for any concept
                 whose mastery is demonstrated by computing a value.

multi_step     — the learner types their working steps and final answer as one response,
                 for a concept where the process matters as much as the result. Graded
                 with the same binary rule; feedback identifies exactly which step broke down.

application    — a brief typed response applying a concept to a short concrete scenario,
                 rather than defining it in the abstract. For concepts whose mastery is
                 really about using the idea.
```

Assign the template once, when a concept first enters scored rotation,
from what kind of mastery that concept represents — not randomly, not by
asking the user. Do not add templates beyond this set of four.

## Primary Scored Concept

Every scored question defines `primary_concept_key` and may define
`supporting_concept_keys`. Only the primary concept receives the binary
confidence update unless the question explicitly contains separately
scored parts. Supporting concepts may inform feedback and future selection
but receive no binary update from one answer.

## Selection Distribution

### Baseline Coverage

A lesson has baseline coverage after at least one independent persistent
scored question whose primary concept belongs to it.

Before every lesson in scope has baseline coverage:

```text
75% — lessons without baseline coverage
25% — known weak concepts and eligible in-scope reviews
```

Within exploration: prioritize untested lessons, vary chapters when
possible, choose representative lesson concepts.

### Targeted Phase

After every lesson in scope has baseline coverage:

```text
50% — weak concepts and review needs
50% — broad variety and coverage expansion
```

Weak allocation priority: repeatedly missed concepts not already reserved
for a due review interrupt, then lowest-confidence tested concepts, then
active review concepts with no pending spaced review.

Broad allocation priority: untested concepts inside sampled lessons,
least-tested concepts, retention checks on stronger concepts, broad
chapter variety.

Do not ask more than two consecutive normal-selection questions from the
same chapter when avoidable.

If baseline coverage already exists from previous sessions, begin in the
targeted phase.

## Due Review Interrupts

Priority, above the normal distribution:

1. assisted immediate retest whose counter has reached zero;
2. other due assisted retests in ascending `queue_order`;
3. eligible independent delayed review;
4. normal distribution.

A due interrupt becomes the next question, does not consume a normal
distribution slot or a batch slot, and the prior distribution resumes
afterward.

## Question Format

First question of a batch, and every question:

```markdown
**Topic:** Chapter [n]: [Chapter Title] — Lesson [n.n]: [Lesson Title]

[Question]

[M] Menu / Save   [E] Explain — or type your answer
```

Answer response:

```markdown
**Session Score:** [correct] / [total] ([%]%)
**Topic:** Chapter [n]: [Chapter Title] — Lesson [n.n]: [Lesson Title]

**Result:** [Correct / Incorrect / Noted — I Don't Know]

**Feedback**
[Concise, direct. Identify what was right or wrong and give the necessary correction.
For a multi_step question, name exactly which step broke down. For a missed hook,
re-teach exactly that edge case before moving on.]

---

### Next Question

**Topic:** Chapter [n]: [Chapter Title] — Lesson [n.n]: [Lesson Title]

[Question]

[M] Menu / Save   [E] Explain — or type your answer
```

After every 5th scored question, show the **Batch complete** block from
`adaptive-study.md` instead of `### Next Question`.

## Feedback Length

Keep feedback brief when understanding is substantially correct. Use a
fuller explanation when the learner selects `E`, says they don't know,
gives a substantially wrong foundational answer, has missed the concept
repeatedly, or needs mechanism-level correction.

## Explain and I Don't Know

`E`, a blank answer, or an explicit statement of not knowing produces
`Result: Noted — I Don't Know`. Treat it as an incorrect independent
engagement. Provide a full explanation and trigger the normal review
cycle.

## Independent Confidence Update

For each independent persistent scored engagement:

```text
Correct outcome = +1
Incorrect or I Don't Know outcome = -1

new_confidence = 0.75 × current_confidence + 0.25 × outcome
```

Then: increment attempts, increment correct/incorrect count, append the
result to the ordered last-two array, set coverage status to `tested`.
Clamp to `[-1.0000, +1.0000]`. Store four decimals, display two.

Do not update confidence for assisted immediate retests.

An incorrect or `I Don't Know` result is a teaching event: it creates the
assisted immediate retest, independent delayed review, and concise
misconception summary below.

## Assisted Immediate Retest

After an incorrect independent answer:

1. explain the concept;
2. create one assisted immediate retest for that teaching event, next
   `queue_order`, `due_after_questions = 2`;
3. ask two unrelated visible scored questions, decrementing after each
   qualifying one;
4. when the counter reaches zero, ask the assisted retest next.

The assisted retest uses different wording, tests the same primary
concept and the same `question_template`, is visibly graded and counts in
the visible session score, but does not update persistent confidence,
attempts, correct/incorrect totals, or coverage, and does not clear the
independent review requirement. It is asked exactly once for that teaching
event. If missed, reteach concisely and leave the delayed review pending.

### Constrained-Scope Retest Fallback

When the selected scope cannot provide two genuinely unrelated scored
questions:

1. use every available distinct unrelated in-scope primary concept once;
2. if only one exists, ask it, then ask the assisted retest;
3. if none exists, ask one materially different unscored spacing/
   application prompt, then the assisted retest — do not store the
   unscored prompt as confidence evidence and do not create another
   assisted cycle from it;
4. keep the ten-question independent delayed review pending for a future
   broader scope.

## Independent Delayed Review

The same incorrect answer creates or refreshes one independent delayed
review due after ten unrelated visible scored questions. A new one gets
the next `queue_order`; refreshing an existing one preserves its order.

It uses a new independent question with the same `question_template`,
updates persistent confidence and counts normally, clears only when
answered correctly with no material factual error, and triggers a new
teaching event and review cycle when missed. Only an independent delayed
review may clear the review item.

## Review Counter Updates

After every visible scored question: determine its primary concept,
identify in-scope review counters, decrement only counters for unrelated
questions, leave out-of-scope counters paused, mark counters `eligible` or
due when conditions are met, apply the due-interrupt priority before
selecting the next question.

## Pending Event Storage

Within the active chat, record compact ordered events only (`event_id`,
`sequence_number`, `primary_concept_key`, `outcome`, `event_type`,
`review_effects`). Allowed event types: `independent_normal`,
`independent_delayed_review`, `assisted_immediate_retest`. Only
independent event types update persistent confidence and attempt counts.
Do not persist question text or full answers. At Menu/Save, re-read
affected rows and replay events in order against the latest stored state.

## Scored Session Summary

When `[M] Menu / Save` is selected and scored questions were asked this
session: leave the pending question ungraded, save all pending ordered
events and review changes, show a concise summary, show only lesson
confidence changes that materially changed, return to the Curriculum View.

```markdown
## Session Summary

**Strengths**
[Concise text summary]

**Weaknesses**
[Concise text summary]

**Work on next**
[Concise recommendation — name the chapter/scope and whether it needs teaching or just more reps]

**Confidence Changes**

Lesson [n.n]: [Lesson Title] — [old] → [new]
Lesson [n.n]: [Lesson Title] — [old] → [new]
```

Omit Confidence Changes when no lesson changed materially. Do not display
raw concept keys or storage details.

---

## Verify (this module's share of the former Final Invariant Check)

- Every scored question has one primary scored concept and one consistent
  `question_template`.
- A `computed_answer` question never offers multiple choice.
- Scored grading is fixed binary with ordered event replay.
- Due assisted retests interrupt normal selection at the correct time,
  without consuming a batch slot.
