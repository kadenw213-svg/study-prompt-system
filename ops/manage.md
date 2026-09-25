# Manage — archive, restore, delete

Commands are typed at `## Select a Class`: `ARCHIVE 1,2` / `ARCHIVE 1-3,5`, `VIEW ARCHIVE`.

## Archive

Show every affected class, then require the exact phrase `ARCHIVE 1-3,5 CONFIRM`. Then, per class: set `index.status = archived`, add an `archive` row. If it's the active class: save its pending state first, clear `state.active_class_key`, and return to `## Select a Class`. Archived classes are excluded everywhere (the class list, Automatic) but their tabs stay intact.

## View Archive

```markdown
## Archived Classes

[1] BIO 1112 — Evolutionary Biology

`RESTORE 1`
`DELETE 1 CONFIRM`

[M] Menu / Save
```
- `RESTORE n`: `index.status = active`, remove the archive row. Don't auto-load it.
- `DELETE n CONFIRM`: permanently delete that class's tab group, index row, and archive row (one explicit confirmation). No `deleted` status is stored.

All three are structural saves: verify before reporting success.

## Workbook health

In the class list or archive view, show one line when there are more than 12 classes (active + archived), more than 90 tabs, or writes keep needing large grid expansions: `Your study memory is getting large — consider archiving classes you've finished.` Never create a second workbook.
