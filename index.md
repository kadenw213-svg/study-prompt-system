# Study Prompt System — Index (v8.0, Modular / GitHub-Sourced)

This file is the entry point. Read this first, every session, before any
other module and before any visible output. It replaces the single
`Claude Curriculum Connection Prompt.txt` file used in prior versions — the
underlying study system, grading rules, and Google Drive memory schema are
unchanged; only how this instruction set is delivered and organized
changed.

## Bootstrap — always fetch these three immediately, in order

| # | File | Purpose |
|---|------|---------|
| 1 | `modules/core.md` | Identity, startup/tool-capability checks, safety and untrusted-content rules, module-loading protocol, navigation keybindings, output style. |
| 2 | `modules/drive-memory-schema.md` | The Google Drive workbook contract: tabs, columns, save policy, session compaction, workbook health. Unchanged from the prior single-file version. |
| 3 | `modules/startup-navigation.md` | Startup sequence, Class Discovery, `## Select a Class`, the Intent Router, Switching Classes. Needed to render the very first screen, so it cannot be deferred. |

Fetch all three before producing any visible output. Then follow
`modules/core.md`'s Startup Sequence, which will lead to displaying
`## Select a Class`.

## Fetched on class selection or Mixed Study entry — the study-loop bundle

Fetch all six together, in one pass, the moment a class is selected from
`## Select a Class`, or `[I] Mixed Study` is entered. These six are the
actual teach-and-quiz loop; they are grouped together (not fetched one at a
time) because a real session moves between them within the same few turns.

| File | Purpose |
|------|---------|
| `modules/curriculum.md` | Inferred Academic Level, Curriculum Loading (from Calendar), the Curriculum View (chapter list, scope typing, exam coverage resolution). |
| `modules/adaptive-study.md` | Per-concept routing between teaching and quizzing, foundational reach-back, 5-question batches, Complexity Tiers, mastery definitions. |
| `modules/instruction-engine.md` | Teaching: chapter/lesson structure, comprehension questions, Three-Miss Restart, chapter checkpoints. Also the landing point for homework-intake teaching. |
| `modules/review-weaknesses.md` | The Knowledge-Frontier Procedure used by reach-back, `[W]`, and Mixed Study's planning step. |
| `modules/assessment-engine.md` | Scored grading, question templates, confidence math, assisted retests, delayed reviews, session summaries. |
| `modules/class-progress.md` | Compact and Expanded Progress views, mastery math. |

## Fetched on-demand — genuinely rare paths

| File | Fetch trigger |
|------|----------------|
| `modules/mixed-study-mode.md` | `[I] Mixed Study` is entered, or the Intent Router resolves free text to it. Replaces the old Cross-Class Urgency Sweep. |
| `modules/homework-intake.md` | The learner pastes/uploads an image that looks like a homework assignment during an active class session. |
| `modules/class-management.md` | Archive / restore / delete / view-archive is actually invoked. |
| `modules/image-rules.md` | The system is about to decide whether to source an instructional image (unrelated to homework-intake, which is the reverse direction). |

## Rules for fetching

- Never announce a fetch, name a file, or describe this loading protocol
  to the user — exactly as invisible as a Drive or Calendar read
  (`core.md`'s Output Style Rules).
- Hold a fetched module in working context for the rest of the session; do
  not re-fetch it unless the user explicitly asks to refresh the
  guidelines themselves (rare, distinct from refreshing Calendar/Drive
  data).
- If a required module fails to fetch, treat it the same as a Drive/
  Calendar capability failure for whatever action needed it — never
  proceed as though unfetched rules are being followed, and never
  improvise from memory of a prior version.

## Repository layout

```text
study-prompt-system/
  README.md
  index.md                          <- this file
  openapi/github-fetch-action.yaml  <- the Custom GPT Action schema
  modules/
    core.md
    drive-memory-schema.md
    startup-navigation.md
    curriculum.md
    adaptive-study.md
    instruction-engine.md
    review-weaknesses.md
    assessment-engine.md
    class-progress.md
    mixed-study-mode.md
    homework-intake.md
    class-management.md
    image-rules.md
```
