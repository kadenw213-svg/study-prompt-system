# Mode: Exam / Quiz Prep

Triggered by selecting or naming a listed quiz/exam, or "prepare me for the exam/quiz …".

## Enter

1. Study bundle loaded; Load class.
2. For "prepare me for the exam tonight/tomorrow/this week": search every active class's cached `exam`/quiz `deadline` rows in that window. Exactly 1 match → use it. 0 or more than 1 → say so plainly, list what was found, and let the user pick.
3. **Coverage resolution** from `calendar_cache.coverage_text`:
   1. parse chapter/unit references (`Ch. 1-3`, `Unit 2`, named lists) with canonicalization;
   2. match them to chapter (and, when specific enough, lesson/concept) keys;
   3. scope = the union of matches in chapter order;
   4. an unmatched reference is listed as unmatched — never silently dropped, and it never narrows the rest.
4. Blank coverage:
```text
This exam has no stated coverage saved on your calendar. Without it, studying this will use the full curriculum. You can also name chapters yourself.

[A] Full Curriculum      [or type chapters from the list above]
```
Never guess coverage from the title or the term position.

## Output (opening)

```markdown
## Midterm — BIO 1112 · Oct 14 (3 days)

Covers Ch 19, 22–31. Biggest gaps first: Ch 27 (untested), Ch 24 (weak). 4 repeat questions from your homework are in scope.
```

## Loop

- Route the coverage set through `engine/route.md` (solid → quiz, weak/unknown → teach, then re-quiz).
- **Bank first**: `bank` rows in the coverage with `seen_count ≥ 2` or `niche: true` → close variants, early and again late in the session.
- For any concept taught at least once, start batches at **Applied** and escalate to **Edge** quickly. Concepts with zero prior exposure start at Building.
- Run the Currency check at each block boundary.

## Exit

Coverage at Working Mastery, or `[M]` → Save → return to the caller (Automatic Scheduler, or the Curriculum View).

## Save

Normal `engine/memory.md` Save. Sessions `mode = exam`.
