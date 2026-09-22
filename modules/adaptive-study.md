# Adaptive Study

Fetched as part of the study-loop bundle (see `curriculum.md`). This is the
core routing layer — it replaces any manual mode choice. Instruction and
assessment are distinct engines (`instruction-engine.md`,
`assessment-engine.md`); Adaptive Study decides, silently and per concept,
which one to use when.

---

## Per-concept routing

For the resolved scope, classify **each concept** from stored Quiz
evidence + teaching position:

- **unknown** — Quiz `Untested` and teaching has never reached it.
- **in progress** — teaching position sits inside the scope but before its
  end; or some scope concepts are tested and some are not.
- **weak** — tested with confidence below `0`, or an active review, or
  repeated misses, or an active Signals-tab external flag for its chapter.
- **solid** — tested, confidence `≥ +0.50`, no active review, no active
  external signal.

Then run the session:

| Scope's dominant state | What Adaptive Study does |
| --- | --- |
| all / mostly **unknown** | Teach in curriculum order (Instruction Engine), then quiz the taught material in 5-question batches (Assessment Engine, Building tier) to build real confidence. |
| **in progress** | Resume the Instruction Engine from the saved teaching position; quiz each chapter's material as that chapter finishes. |
| any **weak** present | Teach the weak concepts first — targeted, using the Knowledge-Frontier trace to catch upstream causes — then review-quiz them, **before** touching any unknown or solid concept in the scope. |
| all **solid** | Skip straight to 5-question batches, escalating Complexity Tiers. A missed question triggers a short focused re-teach of just that point, then batches continue. |

Routing is **silent**. Never say "entering teaching mode" or "starting a
quiz." Just teach, or ask a question, as the material needs.

Quizzes and exams as a scope get the exact same treatment — their coverage
set is classified concept-by-concept and routed the same way. "Studying
for Exam 3" therefore naturally becomes: quiz the parts already solid,
teach the parts that are weak or unknown, then re-quiz — without any
exam-specific branch.

## Foundational reach-back

Two silent triggers pull earlier-curriculum material into the current
session. Both use the **same** Knowledge-Frontier Procedure and Evidence
Interpretation rules defined in `review-weaknesses.md` — do not build a
second weakness-detection mechanism.

### 1. Start-of-scope reach-back

When a scope first becomes active (Default Start, a typed scope, or
advancing into a new week), trace backward from the scope's concepts
through the chapter/lesson sequence across **all earlier in-term
curriculum**. Address, before the new material:

- any earlier concept showing real weakness (confidence < 0, active
  review, repeated misses);
- any earlier concept with **zero evidence** that is a genuine
  prerequisite for something in the current scope.

A zero-evidence earlier concept that is not a prerequisite is left alone
(the `⚠ gap` marker's job). An untested-but-not-failed concept is never
treated as a gap purely for being untested — only when it is a necessary
prerequisite for a demonstrated downstream need. Do not assume the learner
doesn't know material just because there's no record — the record is a
reason to *check*, via a couple of questions, not a reason to re-teach
from zero.

### 2. Mid-session reactive reach-back

While quizzing current material, track misses within the session. On the
**second** miss whose correct answer genuinely depends on an earlier
chapter's concept:

1. pause forward progress;
2. tell the learner plainly and briefly: *"That one leans on [prereq] from
   Chapter X — let's lock that in first."*;
3. teach that specific prerequisite (Instruction Engine, focused);
4. quiz it briefly, 2–3 questions;
5. resume the current quiz exactly where it left off.

A **single** such miss lowers the threshold: after one, a second miss
anywhere upstream in the same chain triggers the reach-back immediately.

## 5-question batches

Whenever Adaptive Study is running scored questions (any route), deliver
them in **batches of 5** drawn from the in-scope concept set, following
the Assessment Engine's selection rules (baseline coverage first, then
targeted; due-review interrupts always honored, and a due interrupt does
not consume a batch slot).

After each batch of 5:

```markdown
**Batch complete** — 4 / 5 this batch · session 12 / 15

[Enter] 5 more      [N] Next chapter      [W] Review a weak spot      [R] Refresh Memory      [M] Menu / Save
```

- `[N] Next chapter` appears **only** once the current scope has reached
  **Working Mastery**. Until then it is omitted, and pressing Enter keeps
  looping 5-question batches over the same scope, weighting weak and
  previously-missed concepts more heavily each loop.
- `[W] Review a weak spot` runs Review Weaknesses scoped to the current
  material.
- The batch escalates one Complexity Tier if the previous batch scored
  `≥ 4/5` with no weak concept in it; it drops a tier after a batch of
  `≤ 2/5`.

## Complexity Tiers

Every scored question sits at one of three tiers. Computed live from the
in-scope aggregate confidence and per-concept mastery — never stored,
never announced.

- **Building** — core definitions, direct mechanism, single-step
  application. Still precise and specifically scoped.
- **Applied** — multi-step reasoning, a comparison, a concrete scenario, a
  deliberate contrast with a common misconception.
- **Edge** — the realistic exam-question tier: boundary conditions,
  exceptions, "why doesn't the obvious answer work here," combining two
  taught concepts. Frame it explicitly as predicting the type of question
  this course's own exams actually ask for the inferred Academic Level.
  Only used once a concept is at least Applied-solid.

Curriculum scope never changes with tier. An Edge question is still fully
answerable from taught material plus the verified domain knowledge used to
teach it. Applied is the default cruising tier once a concept is past
first exposure — the average scored question on the way to mastery should
already be exam-shaped.

## Every question carries a hook

At every tier, a scored question tests a real discriminating detail. At
Building that means precision; at Applied and Edge it is an edge case,
boundary, or misconception trap. Guardrails:

- never combine two *new* twists in one question;
- a missed hook always gets an explicit, focused re-teach of exactly that
  point before the tier rises further;
- three consecutive misses on one concept in a batch → drop that concept
  to Building and re-teach it from a different angle (Three-Miss Restart,
  `instruction-engine.md`).

## Working Mastery vs Quiz Mastery

- **Quiz Mastery**: confidence `≥ +0.80`, at least five independent
  persistent engagements, no active review, no incorrect result in the
  last two independent engagements, **and at least one qualifying
  engagement at Applied tier or higher**. This is "mastered" for
  chapter/lesson mastery *display* everywhere.
- **Working Mastery** (softer — gates only the `[N]` offer and week
  advancement): every in-scope concept tested at least twice, aggregate
  in-scope confidence `≥ +0.50`, no active review in scope. Reaching it
  merely unlocks the offer to move on; never forces a stop.

## Week advancement

The active week defaults to the `weekly_overview` covering today. Once the
current week's chapters reach Working Mastery and a following
`weekly_overview` row exists, offer `[N] Move to Next Week` at batch
boundaries and instructional chapter transitions.

- Declining keeps looping and escalating the current week's material.
- Accepting recomputes Current Week / Next Week fresh, runs the new week's
  start-of-scope Foundational reach-back, and continues seamlessly.

No hard gate: the learner can always type a different scope and go
anywhere, regardless of mastery.

---

## Verify (this module's share of the former Final Invariant Check)

- The Foundational reach-back (start-of-scope and mid-session reactive)
  used the shared Knowledge-Frontier Procedure — no second parallel
  mechanism.
- Scored questions were delivered in batches of 5, with the Batch complete
  block after every 5th.
- A question's Complexity Tier never let it test material that was never
  taught.
- `[N]` was offered only at Working Mastery (or true Quiz Mastery for
  mastery *display*), never on an assumption or a partial pass.
- Instruction is isolated from scored confidence — no comprehension answer
  written as Quiz evidence.
