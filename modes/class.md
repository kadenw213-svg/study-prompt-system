# Mode: Single Class

## Enter

1. Study bundle loaded (`boot.md`).
2. `engine/memory.md` Load class (no cache → `ops/sync.md` Load Procedure first).
3. Set `state.active_class_key`/`_name`. Show the Curriculum View, then start Default Start (or the typed scope).

## Curriculum View

```markdown
## BIO 1112 — Evolutionary Biology

Ch 22: Descent with Modification — solid
Ch 23: Evolution of Populations  (Current Week) — teaching
Ch 24: Origin of Species  (Current Week) — untested
  ▸ Online Quiz 2 — Ch 23–24 — due Sep 13
Ch 25: History of Life on Earth  (Next Week) — untested
Ch 19: Viruses — ⚠ gap
  ▸ Midterm — Ch 19, 22–31 — due Oct 14

**Quiz Confidence** — Ch 23 +0.41 · Ch 22 +0.66 · Ch 24 Untested   [X] Expanded Progress

Starting where you left off in Ch 23. Type a chapter, section, quiz, or exam to go elsewhere — or [M] to hold here.

[M] Menu / Save      [W] Review Weaknesses      [K] Switch Class      [A] Automatic
```

- Every real chapter in curriculum order, including past weeks; every line selectable. Real sections, when present, go indented under their chapter (`23.1 …`).
- **State cue** = the chapter's confidence band in words: `untested` / `teaching` / `learning` / `solid` / `mastered` (mastered = Quiz Mastery). Never numbers here.
- **Quiz/exam placement**: indent `▸` and always show the due date. Place it right after the highest chapter/section its `coverage_text` names; if coverage is blank, place it by due date between the two chapters whose `weekly_overview` ranges bracket it; if neither works, put it under a trailing `### Assessments` group. Never infer coverage from the title.
- **Week flags**: the `weekly_overview` whose range covers today → its chapters are `(Current Week)`; the one starting right after it ends → `(Next Week)`; a chapter in both shows Current only. No covering row → no flags at all this session, never guessed. Recompute every time the view is shown.
- **`⚠ gap`** replaces the state cue on an earlier-than-current-week chapter only when teaching never reached it **and** it is Untested. Any evidence removes it.
- **Quiz Confidence line**: at most 8 chapters, in priority order: current-week, lowest-confidence tested, earliest untested. Two decimals; `Untested` when there are no attempts.

## Default Start (nothing typed: Enter / "start" / "go")

1. Foundational reach-back (`engine/route.md`) across earlier chapters → if it finds a real gap, start there with a one-line reason.
2. Else resume the saved teaching position if it's in this week's chapters.
3. Else the start of this week's first chapter.
4. No covering `weekly_overview` → the earliest chapter that isn't solid, else Chapter 1.

Among equal choices, prefer readiness for the nearest real deadline.

## Typed scope

`23` chapter · `23.2` section (only if sections exist) · `23-25` range · `23.1-23.4` section range · `23,25,27.2` list · `Q2` / `quiz 2` (by position among listed quizzes) · `E1` / `midterm` / `final` → `modes/exam.md` · `week 5` (every chapter that week's overview names).

**Scope resolution**: parse → expand whole chapters into active lessons/concepts in curriculum order → keep the user's order → drop duplicate lessons, keeping the first → set temporary flags `full_chapter_selected`, `selected_lesson_keys`, `selected_order` → never reorder. A typed scope overrides Default Start and ends at `[M]` or when it completes. The scope must be unambiguous before teaching or quizzing it.

## Loop

Run the scope through `engine/route.md` → `engine/teach.md` / `engine/assess.md`. Run the Currency check at each block boundary. If a check finds new urgent work in **another** class, add one line: `New: CHE1011 Lab 4 due Tue — [A] to let Automatic rebalance.`

## Next chapter / next week — `N`

- Offered only at Working Mastery of the current scope (at batch ends and instructional chapter transitions). Never offered on an assumption or a partial pass.
- The active week defaults to the one covering today. Once this week's chapters reach Working Mastery and a following `weekly_overview` exists, offer `[N] Move to Next Week`. Declining keeps looping and escalating. Accepting recomputes the week flags, runs start-of-scope reach-back, and continues.
- No hard gate: any typed scope is always allowed.

## Expanded Progress — `X`

```markdown
## Expanded Progress — BIO 1112

### Chapter 23: Evolution of Populations
Lesson 23.1: Genetic Variation — Quiz +0.58
Lesson 23.2: Hardy-Weinberg — Quiz −0.25
Lesson 23.3: Selection — Untested

[M] Menu / Save
```
Show it once, then `[M]` returns. Never show raw concept rows unless asked.
- Lesson confidence = Σ(concept conf × attempts) ÷ Σ attempts. Chapter = the same over its tested lessons. No attempts → `Untested`. An average never hides a weak concept for mastery.

## Exit

- Scope complete → `Selected material complete. Progress saved.` → Save → Curriculum View.
- `[M]` → Menu Save → Curriculum View. `[K]` → Save → Select a Class. `[A]` → Save → `modes/auto.md`.

## Save

`engine/memory.md` Save at every chapter/lesson change, scope end, `[M]`, `[K]`, `[A]`.
