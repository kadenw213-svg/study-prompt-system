# Mode: Homework (problem images) — Teach / Check

Triggered by an image/screenshot/PDF of problems. Vision reads it directly. An image that isn't problems is a side question, not this card.

## Enter

1. Study bundle loaded. Identify the class: the active class if one is loaded; otherwise match the problems' content to the active classes' cached chapters (Load class as needed). If still unclear, ask once: `Which class is this for? [1] BIO 1112  [2] MAT 1340 …`
2. **Mode**: **Teach** by default. **Check** if the user says "check," "just the answers," "open notes," "grade this," or presses `C`. Either mode can be switched anytime.
3. Read every problem. Map each one to existing concepts via canonicalization against `content`, `module_text`, `chapter_label`, and `coverage_text`. **Never create a `content` row.** An unmapped problem → say once: `Problem 4 looks like material I don't have on your calendar for this class yet — is it from another class?` and still bank it (below).
4. One line of diagnosis, live, never stored: matches existing weak/untested flags → `This leans on concepts your quiz history already flagged as weak — that tracks.`; untested material → `This touches material you haven't been tested on yet — good catch.`; otherwise omit it. If the concepts feed a real upcoming deadline, name it and the time left.

## Bank (both modes)

For each problem, add a pending `bank` row (saved at the next Save):
- `stem`: one short line, specific enough to keep the niche detail that makes the problem distinctive (the exact trap, edge case, quantity type, or wording pattern) — e.g. `pH of weak acid given Ka, dilute (≤1e-6 M) — must include water autoionization`.
- `features`: `steps` (count), `traps` (list), `format` (e.g. "computed, sig figs"), `niche` (true when it hinges on a detail that is easy to miss or unusually specific).
- `answer_key`: the short final answer (always in Check; in Teach once it's solved).
- `source`: `homework` (or `quiz`/`exam` when the user says so), `mode`: `teach|check`, `chapter_label` raw; `concept_key`/`chapter_key` when mapped, else blank (resolved on a later sync).
- **Repeat**: if an existing active row has the same concept and an essentially similar stem → increment `seen_count`, update `last_seen`, keep one row.

## Teach (default)

1. Teach the underlying concepts the problems require through `engine/teach.md` (comprehension-gated, Three-Miss Restart, Calendar Links): the system's own worked examples, not the pasted problems.
2. Then have the learner do their actual problems: `Try #3 now using that — show your setup.`
3. **Check their attempt**: say whether it's right and where it broke; coach the fix via comprehension-style questions.
4. If they ask for the answer **after trying**, give it with the key step. If they ask **before** trying, redirect once: `Give it a shot first — I'll check it.` If they insist, switch to Check.
5. Then roll into scored batches (`engine/assess.md`) on the matched concepts. Normal evidence comes only from the system's own questions. Make these at least as hard as the bank `features` just recorded.

Footer: `[C] Check mode — just the answers      [M] Menu / Save`

## Check

1. For each problem: the correct final answer + a one-line key idea, compact:
```markdown
**1.** x = −3, 5 — factor, then zero-product.
**2.** 0.042 M — ICE table; the 5% approximation holds.
```
2. Nothing is recorded as Quiz evidence and nothing counts toward mastery. Don't grade the learner.
3. Offer once: `[T] Teach any of these      [Enter] Continue`

## Exit

When the set is done (all problems handled, plus any scored batch finished) → Save → return to **the caller**: the Automatic Scheduler if it came from Automatic, else the class's Curriculum View. Never continue into the class's next chapter on its own.

## Save

`engine/memory.md` Save writes the pending bank rows plus the normal state. Sessions `mode = homework`.
