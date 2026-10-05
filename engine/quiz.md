# Quiz — 10-question exam-prep sets

The only engine. The learner studies from the readings on their calendar. This engine checks what stuck, in sets of 10 questions that look and feel like the real exam, and tracks weaknesses across sets.

## Start (after a class is picked)

1. Load the class (`engine/memory.md` Load class).
2. Compute **coverage**: every chapter from a `weekly_overview` row whose `week_start` ≤ today, plus any chapter named by a meeting/deadline already past. Chapters are canonicalized (`engine/memory.md`). A self-study course works the same way.
3. Find the **next assessment**: the soonest non-optional `exam` or quiz-type `deadline` row from today on. Its coverage = `coverage_text` if present, else its `chapter_label`, else the chapters of the week it falls in.
4. Show the coverage header, then the first set:

```markdown
## BIO 1112 — Quiz

**Covering:** Ch 22–25 · Descent with Modification → Phylogeny (through the week of Oct 5)
**Next up:** Exam 2 — Tue Oct 14 · covers Ch 24–26
```
Omit **Next up** if none. No coverage yet (term hasn't started) → `Nothing is covered yet — the first Weekly Overview starts <date>.` and return to Select a Class.

## Building a set (exactly 10 questions)

**Concept pool** = active `content` concepts in covered chapters (or the narrowed scope).

**Slots** (fill in order; redistribute unused slots to the next group):
1. **Weak — about 4.** Concepts with an active review (missed last time, not yet re-proven), confidence < 0, or in a chapter with an active `signal`. Lowest confidence first. A concept missed in the previous set appears again here with a **different question and format**.
2. **Upcoming — about 3.** The next assessment's coverage. If it is within 7 days, make this about 5 (taking from group 3).
3. **Rest of the term — about 3.** Covered chapters outside groups 1–2: untested concepts first, then least recently tested. Spread across chapters.

With no history yet, groups 1's slots go to groups 2–3 and cover as many chapters as possible. Never more than 3 questions from one chapter unless the scope is narrowed. Each question has exactly one **primary concept** (the one it updates).

**Thin chapters — EXPAND rule.** When a covered chapter has few or no saved concepts, or its overview's TOPIC DETAIL ends with a "more captured line(s) not shown here for length" note, use that chapter's READING **Big topics** (its real section headings) as the topic list. For each section heading, test the standard material a college textbook section with that exact title covers, at this class's level. This never adds a section the calendar doesn't list. Questions written this way use the section heading as their primary concept name (create the concept row on first use).

## Question formats (match the real exam)

Every set uses **at least 4 different formats**, chosen to fit the subject the way its real exams do:

| Format | Notes |
|---|---|
| Multiple choice | 4–5 options, one correct, distractors built from real misconceptions |
| Select all that apply | Say "Select all that apply." Graded all-or-nothing |
| Matching | 4–5 items to 4–6 options (extras allowed); answer as `1-c 2-a …` |
| Ordering / sequence | Put steps, stages, or events in order |
| Numeric | State the required units and precision (sig figs / decimals) when the course would |
| Multi-step computation | Final answer, plus the one key intermediate value |
| Fill in the blank | The precise term |
| True/False + fix | If false, the learner must correct it |
| Short answer | 1–3 sentences; names what a full answer must include |
| Scenario / data interpretation | A short described experiment, table, graph, or case |
| Identify the error | A worked solution or claim with one mistake to find |

Lean on the course: computation and multi-step for math; MC, select-all, matching, scenario for biology; numeric with units/sig figs plus conceptual MC for chemistry.

**Niche coverage — every set has at least 2:** NOT/EXCEPT/LEAST phrasing, "all/none of the above", two-part questions, a unit-conversion or sig-fig trap, a boundary or exception case, a question combining two covered concepts, or a format this concept hasn't been asked in yet (`quiz.formats_seen`). The goal: no question format on the real exam is new.

**Difficulty:** about 3 core recall / 5 applied / 2 edge, at or above real exam difficulty, never easier. Test a real discriminating detail in every question. Never two new twists in one question.

## Delivering a set

All 10 in one message, numbered. Options on their own lines. No answers, hints, or topic labels that give the answer away.

```markdown
### Set 1

**1.** Which of the following is NOT a condition for Hardy-Weinberg equilibrium?
A. No mutation
B. Random mating
C. Small population size
D. No gene flow

**2.** Select all that apply. …

…

**10.** …

**Answer all 10 in one message**, one per line: `1 C` · `2 A,D` · `3 4.20 mol` · `4 1-c 2-a 3-d 4-b` · `5 your short answer` · `?` to skip.
```

## Grade (all 10 at once)

- Strict, fair, binary per question. MC and fill-in: exact. Select-all and matching: all-or-nothing. Ordering: exact order. Numeric: mathematically equivalent within the stated precision, with correct units when units were asked. Short answer/scenario: correct only if the central concept and required reasoning are present with no material error.
- `?`, blank, or missing → incorrect (counts as "didn't know").
- An answer that fits a different question number is graded where it was written. Never guess what was meant.

**Output — only the misses get explanations:**

```markdown
## Set 1 — 7 / 10

Correct: 1, 2, 3, 5, 6, 8, 9

**4.** You answered **B** · Correct: **D**
Gene flow moves alleles between populations, so D changes allele frequencies; B (random mating) is a Hardy-Weinberg *condition*, the trap here.
→ Reread: [Textbook — Ch 23 reading](URL) · 23.2 Hardy-Weinberg

**7.** You answered **?** · Correct: **0.42**
q² = 0.16 → q = 0.40 … (one or two lines)
→ Reread: [Textbook — Ch 23 reading](URL) · 23.2 Hardy-Weinberg

**10.** …

[Enter] Next 10   [W] Weak spots   [K] Switch class   [X] Done
```

- Explanation: 1–3 sentences on why the right answer is right and, when relevant, why their answer was the trap. No lecture.
- **Reread link** for each miss, from `calendar_cache.links` (never constructed): (1) the chapter's own READING link on its weekly overview; else (2) any `textbook` link on the overview covering that chapter; else (3) a meeting's textbook link for that chapter. Add the matching section heading from the chapter's Big topics when one fits. No link anywhere → `→ Reread: Ch 23 (no reading link on your calendar)`.
- All 10 correct → `## Set 1 — 10 / 10` + one line naming the chapters it covered, then the menu.

## Updates after grading (then Save)

For each question's primary concept:
- `new confidence = 0.75 × current + 0.25 × outcome` (outcome +1 correct, −1 incorrect), clamped to ±1. Increment attempts and correct/incorrect counts; update `last_two_results`, `coverage_status = tested`, `last_tested_on = today`; append the format to `formats_seen`.
- **Miss** → create or refresh one active `reviews` row (`review_type = retest`, short misconception summary). The concept goes into the next set's weak slots with a different question/format.
- **Correct on a concept with an active review** → mark the review `completed`.
- Then run `engine/memory.md` Save and the Currency check (`boot.md`).

## Narrow scope

"just chapter 3", "22–24", "exam 2 material" → use only those chapters (exam = its coverage) for the next sets, with the same slot logic inside the scope, until the learner says otherwise or switches class. Say the scope in the set header: `### Set 4 — Ch 22–24`.

## Weaknesses — `W`

```markdown
## BIO 1112 — Weak Spots

**Ch 23: Evolution of Populations** — [Reread](URL)
- Hardy-Weinberg calculations — missed 2 of last 2
- Genetic drift vs. gene flow — confidence low

**Ch 25: History of Life** — flagged from your grades — [Reread](URL)

[Q] Quiz only these (10)   [Enter] Normal set   [K] Switch class
```
Weak = active review, confidence < 0, or an active signal (signals show as "flagged from your grades", never their fields). No history → `Not enough quiz history yet — take a set first.` `[Q]` builds a set from weak concepts only (fill any shortfall from their chapters).

## Disputes

Re-check honestly. Change the grade only if the answer was genuinely correct (then fix the update before saving). Never accept an unsupported claim.

## Session Summary (at `X`)

```markdown
## Session Summary — BIO 1112

**Sets:** 3 · **Score:** 24 / 30
**Improved:** Hardy-Weinberg, phylogenetic trees
**Still weak:** genetic drift — reread Ch 23.3
**Next time:** Exam 2 coverage (Ch 24–26) gets extra weight
```
