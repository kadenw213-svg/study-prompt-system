# Review Weaknesses

Fetched as part of the study-loop bundle (see `curriculum.md`).

## Purpose

A callable procedure that analyzes the currently loaded class and builds a
temporary instruction plan aimed at the learner's real knowledge gaps. It
is invoked automatically by Adaptive Study's routing and Foundational
reach-back (`adaptive-study.md`), by Mixed Study Mode's planning step
(`mixed-study-mode.md`), and directly by `[W]` from a batch boundary or the
Curriculum View.

It may read: Quiz confidence, Quiz attempts, repeated Quiz misses, active
Quiz review items, low-certainty legacy historical signals, an active
Signals-tab flag, and the curriculum's chapter/lesson sequence.

It must not: use comprehension answers as evidence, write Quiz confidence,
write Quiz review state, or persist the temporary plan.

## Knowledge-Frontier Procedure

Build the temporary plan deterministically:

1. identify target concepts from active reviews, negative evidence,
   repeated misses, and the lowest-confidence tested concepts below
   mastery;
2. when no absolute weakness signal exists but assessment evidence does,
   rank the least-confident tested concepts relative to the rest of the
   curriculum and begin with the most foundational among them;
3. trace every target backward through the chapter/lesson sequence;
4. identify the deepest prerequisite demonstrated reliably;
5. identify the first weak, contradictory, or necessary-untested
   prerequisite immediately above that demonstrated frontier;
6. create candidate instructional starting points;
7. rank candidates by: number of weak downstream concepts, foundational
   depth, repeated misses, negative Quiz confidence, relative low
   confidence below mastery, certainty of evidence;
8. build a valid lesson path from foundations toward dependent weaknesses;
9. collapse duplicate lessons;
10. order the plan from the most foundational recommended starting point
    upward.

## Evidence Interpretation

- weak: confidence below `0`, active review, repeated misses, or an active
  Signals-tab external flag for its chapter;
- strong: confidence at least `+0.50` and no active review and no active
  external signal;
- legacy historical signal: lower-priority evidence only, never mastery;
- tested but below mastery with no absolute weakness: relative review
  candidate, ordered from least confident toward more confident.

Untested concepts are not classified as weaknesses, but may be included
when they are necessary prerequisites for a demonstrated downstream gap. A
zero-evidence concept that is a prerequisite for current-scope material is
checked with a few questions before being taught — the absence of a record
is a reason to verify, not to assume ignorance.

## When invoked directly by `[W]`

Show the plan and let the learner pick a starting point:

```markdown
## [Course Code] — Review Weaknesses

Recommended starting point:

**Chapter [n]: [Chapter Title]** — Lesson [n.n]: [Lesson Title]

[1] Lesson [n.n]: [Lesson Title] — foundational weakness
[2] Lesson [n.n]: [Lesson Title] — weakness

[A] Load all recommended      [M] Menu / Save

Type a number, or A.
```

The plan then runs through the normal Instruction Engine flow and is
discarded when complete or on Menu.

## No Reliable Evidence

```markdown
## Review Weaknesses

There is not enough assessment history to identify reliable weaknesses.

Beginning with the curriculum foundation.
```

Then begin instruction at the earliest active chapter and lesson.
