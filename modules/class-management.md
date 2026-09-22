# Class Management

Fetched on-demand — the first time archiving, restoring, deleting, or
viewing the archive is actually invoked. Not needed for normal study flow.

---

`[K] Switch Class` from anywhere returns to `## Select a Class`. From
there:

```markdown
## Select a Class

[1] BIO 1112 — Evolutionary Biology
    Week of Sep 1 · Ch 23–24 · teaching in progress · 3 reviews due · 2 Hours of curriculum Remain
[2] MAT 1340 — College Algebra
    Week of Sep 1 · Ch 2 · not started this week · ⚠ earlier gap

`ARCHIVE 1,2` — archive classes (e.g. after a semester ends)
[A] View Archive
[R] Refresh Class List

Select a class to continue.
```

Status-line construction is identical to `## Select a Class`
(`startup-navigation.md`'s Curriculum Time Remaining section) — not a
second mechanism.

## Archiving

Support lists and ranges: `ARCHIVE 1-3,5`. Show every affected class and
require exactly `ARCHIVE 1-3,5 CONFIRM` before executing.

If the active class is archived: save eligible pending state, mark it
archived in `index`, add its archive row, clear active class, return to
`## Select a Class`.

## Archive Menu

```markdown
## Archived Classes

[1] [Course Code] — [Course Name]

`RESTORE 1`
`DELETE 1 CONFIRM`

[M] Menu / Save
```

`RESTORE` sets index status to `active` and removes the archive row; it
does not automatically load the class. `DELETE ... CONFIRM` permanently
removes the class's tab group, index row, and archive row after that one
explicit confirmation.
