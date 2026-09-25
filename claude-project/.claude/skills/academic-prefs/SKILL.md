---
name: academic-prefs
description: View or change academic-sync preferences (target calendar, event color, timezone, default due time, room/location mappings, whether administrative dates are calendarized, D2L base URL, etc). Use when the user wants to inspect or change how academic-import behaves, without doing a scan or sync.
user-invocable: true
---

# /academic-prefs -- manage academic-sync preferences

Arguments passed: `$ARGUMENTS`.

This skill is a thin, careful wrapper over `uv run academic-sync prefs ...`
(run from the `academic-sync` project root). It never scans D2L and never
writes to Google Calendar -- if the user wants to change *behavior for the
next sync*, this is the right skill; if they want to *run a sync*, redirect
them to `/academic-import` (a brand-new course's first scan) or
`/academic-sync` (recurring maintenance -- light re-scan, link refresh,
weekly grade diagnostic on a course already scanned before).

## Dispatch on arguments

### No args, or `list` -- show current preferences

```bash
uv run academic-sync prefs list
```

If the user seems unsure what's settable, also show:

```bash
uv run academic-sync prefs list --known
```

which prints every known preference key with its default and description --
useful context, but don't dump it unprompted every time; only when they ask
"what can I configure" or the plain `list` came back mostly empty.

### `get <key> [--course <id>]`

```bash
uv run academic-sync prefs get <key> [--course <id>]
```

### `set <key> <value> [--course <id>]`

```bash
uv run academic-sync prefs set <key> <value> [--course <id>]
```

Before setting, sanity-check the key against the known list
(`prefs list --known`). If it's not a known key, tell the user and ask
whether they really want a custom key (pass `--force` to `prefs set` only
if they confirm) -- an unrecognized key is much more likely a typo than an
intentional new preference.

**Never call `prefs set` from a casual mention in conversation.** Only set a
preference when the user is explicitly telling you to configure something
("set the default due time to 5pm," "use my second calendar," "the lecture
room is always Centennial Hall 204") -- or when `/academic-import` relayed
an explicit confirmation from the user mid-scan (e.g. answering "which room
is lecture vs. lab?"). See CLAUDE.md invariant 11.

Course-scoped preferences (`--course <id>`) override global ones for that
course only -- use this for things like a room mapping that's specific to
one class.

### `unset <key> [--course <id>]`

```bash
uv run academic-sync prefs unset <key> [--course <id>]
```

Confirm with the user before unsetting something that clearly has
real-world consequences next sync (e.g. `target_calendar_id`,
`invite_guests`) -- for most keys (a room mapping, `default_due_time`) just
do it, since it's easily reversible.

## Common preferences worth knowing about

| Key | What it controls |
|---|---|
| `target_calendar_id` | Which Google Calendar events are written to (default: `primary`) |
| `calendar_color_id` | Google Calendar colorId for school events (default: `10`, dark green) |
| `default_reminders_enabled` | Whether created events use Calendar's default reminders (should stay `False`) |
| `invite_guests` | Whether instructor/classmates are ever added as guests (should stay `False`) |
| `create_meet_links` | Whether Meet links are auto-attached (should stay `False`) |
| `timezone` | IANA timezone for all dates/times (default: `America/Denver`) |
| `default_due_time` | Time of day used when a source gives a date but no time (default: `23:59`) |
| `include_topic_in_class_titles` | Whether class titles include a parenthetical topic |
| `administrative_dates_calendarize` | Whether drop/withdrawal/registration deadlines become events |
| `d2l_base_url` | Institution D2L/Brightspace base URL |
| `diagnostic_color_red` | Google Calendar colorId for a RED "Previous Week Diagnostic" banner (default: `11`, Tomato) |
| `diagnostic_color_yellow` | Google Calendar colorId for a YELLOW diagnostic banner (default: `5`, Banana) |
| `diagnostic_color_green` | Google Calendar colorId for a GREEN diagnostic banner (default: `2`, Sage) |

Room/location mappings and source-precedence overrides don't have fixed key
names yet in this MVP -- use a descriptive custom key (e.g.
`room_mapping.BIO1112_lecture`) with `--force`/course scope, and mention to
the user that free-form preference keys like this aren't yet validated
beyond "does it look like a typo."

## After any change

Confirm back to the user in one line what changed and, if relevant, that it
takes effect on the *next* `/academic-import` run (preferences don't
retroactively touch already-synced Calendar events).
