# Class Progress

Fetched as part of the study-loop bundle (see `curriculum.md`). There is no
standalone class menu — selecting a class goes to the Curriculum View.
Progress is reachable from there.

## Compact progress (shown under the Curriculum View header)

```markdown
## Quiz Confidence

Chapter 1: Cellular Biology — +0.41
Chapter 2: Cellular Energy — -0.18
Chapter 3: Genetics — Untested

[X] Expanded Progress
```

Show at most eight chapter rows, prioritizing: current-week chapters,
lowest-confidence tested chapters, earliest untested chapters.

## Expanded Progress — `X`

```markdown
## Expanded Progress — [Course Code]

### Chapter 1: Cellular Biology
Lesson 1.1: Cell Theory — Quiz +0.58
Lesson 1.2: Cell Structure — Quiz +0.44
Lesson 1.3: Mitosis — Quiz -0.25
Lesson 1.4: Meiosis — Untested

[M] Menu / Save
```

Do not expose raw concept rows unless specifically requested.

## Confidence Status

Untested concepts, lessons, and chapters display `Untested`. Never display
untested confidence as `0` or `50%`. Displayed averages never override
weak individual concepts for mastery.

## Lesson / Chapter Quiz Confidence

```text
lesson_confidence = sum(concept_confidence × concept_attempts) ÷ sum(concept_attempts)
```

Chapter confidence aggregates tested lessons using total concept attempts
as weights. If no concept/lesson has attempts, display `Untested`.

## Quiz Mastery

A concept is mastered only when: confidence at least `+0.80`; at least
five independent persistent scored engagements; no active review; no
incorrect result in its last two independent engagements.

A lesson is mastered only when every active concept is tested and
mastered, and no active lesson review item exists. A chapter is mastered
only when every active lesson is mastered.

Working Mastery (Adaptive Study's softer `[N]` gate, `adaptive-study.md`)
is a separate, softer definition — do not conflate the two.

---

## Verify (this module's share of the former Final Invariant Check)

- Untested state displays as `Untested`.
