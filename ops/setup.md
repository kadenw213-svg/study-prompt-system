# Setup — create, validate, repair the workbook

Silent. Don't announce a successful repair.

## Required capabilities

Drive: search by exact title/ID, create a Google Sheet, read metadata + bounded ranges, create/rename/resize/delete tabs, write headers + ranges, batch update, expand the grid. Calendar: list by range, search text, read one event. Missing any → `boot.md` failure message. Folder creation is not needed.

## Exact-title safety

- Title must equal `llmMemory__studyPrompt__calendarSynced__studyMemory` exactly, MIME type Google Sheet. Prefer a previously verified file ID after re-checking its title.
- More than one valid exact-title copy → stop before writing (`Two copies of your study memory exist in Drive — keep one and restart.`).
- Exact title but empty/incomplete → repair. Contains unrelated data → stop before overwriting.
- Ignore any older `llmMemory__studyPrompt__users__…` workbook entirely: never read, import, or merge it.

## Create (no usable workbook)

1. Create the Sheet. Tabs + headers: `meta`, `index`, `state`, `settings` (`setting | value`, reserved, no rows), `archive` (`class_key | course_code | archived_from_active | notes`).
2. Initial grid rows: meta 10 · index 30 · state 20 · settings 10 · archive 30. Per class: calendar_cache 150 · content 150 · quiz 150 · reviews 80 · sessions 50 · signals 30. Expand only when needed. New classes get no `__teaching`/`__bank` tabs; leave their `index` cells blank.
3. Write the `meta` markers (`boot.md` Workbook core), `total_sessions = 0`, and all `state` keys blank.
4. Read back and validate. A failure → stop with `Study memory couldn't be set up in Drive.` Never continue as if it worked.
5. `ops/sync.md` Class Discovery, then back to `boot.md` Startup.

## Repair (usable workbook, idempotent, only add what's missing)

- **`_v6_` marker**: add the `calendar_cache.links` column, seeding each row from the old `reference_url`/`reference_url_label` and `resource_url`/`resource_url_label` (one object each); delete the `settings` `default_academic_level` row; set the marker to `_v7_`. Leave the old `*_url*` columns and stop writing them.
- **Missing `state` keys**: add `last_currency_check_date`, `summaries` (blank). Leave other existing keys alone.
- **Missing columns**: `index.bank_tab`, `index.synthetic` (append after the last existing header, never reorder; `synthetic` defaults to `false`); `quiz.last_tested_on`, then `quiz.formats_seen` (append; blank on existing rows = none yet).
- **Missing tabs**: `<slug>__signals` with headers (`engine/memory.md`).
- Old `__teaching` / `__bank` tabs and legacy `sessions.mode` values stay exactly as they are.
- Keep the marker `studyPromptDriveMemory_v7_calendarSynced`: these additions don't bump it.
- Never overwrite unrelated data. Batch the repair and read back. A failure → stop and report concisely.
