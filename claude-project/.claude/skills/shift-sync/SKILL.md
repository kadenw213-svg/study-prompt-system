---
name: shift-sync
description: Mirror work shift events from the user's YMCA shift-schedule calendar into their main Google Calendar, using the same no-guests/no-reminders/clean-title formatting rules as academic-import, without ever creating duplicates. Use when the user asks to sync/copy/import their YMCA shifts, or update their work schedule on their main calendar.
user-invocable: true
---

# /shift-sync -- mirror YMCA shifts onto the main calendar

Arguments passed: `$ARGUMENTS` (optionally a number of days to look ahead;
default 21 if not specified or not a plain integer).

This is a small, separate skill from `/academic-import` -- it doesn't touch
the `academic_sync` Python package or its database at all. It's a direct
one-way mirror between two Google Calendars, done live with the Calendar
connector tools. It follows the same formatting principles established for
`/academic-import` (see CLAUDE.md and `docs/calendar_rules.md`) but doesn't
need the full extraction/completeness pipeline -- there's no parsing
involved, just copying real calendar events with reformatting.

## Source and target

- **Source calendar**: the `shift_source_calendar_id` value in
  `config/personal.local.md` (gitignored; if missing, ask the user for it
  once and save it there) -- this is an ICS-imported calendar (Google reports `accessRole: reader`
  even though it belongs to the user, which is normal for import-type
  calendars) that the user has privately relabeled "YMCA" in their own
  Google Calendar sidebar. Its `summary` field via the API is literally
  "My Schedule" -- that's expected, not a sign you have the wrong calendar.
  If `list_events` against this ID ever 404s or comes back empty when the
  user says shifts exist, stop and ask them to re-confirm the calendar ID
  via Settings and sharing -> Integrate calendar, since a resource could
  have been recreated with a new ID.
- **Target calendar**: the user's primary calendar (omit `calendarId` on
  the Calendar tools, which defaults to primary).

## Formatting rules (apply every time, no exceptions)

- **Title**: `YMCA - <original event summary>` (e.g. source `"Farm -
  Lifeguard - Mid-day"` becomes `"YMCA - Farm - Lifeguard - Mid-day"`). No
  checkbox characters.
- **No attendees ever** -- the source events may have organizer/attendee
  metadata from the scheduling system; never carry that into the mirrored
  event. Don't pass `attendees` to `create_event`/`update_event`.
- **No Google Meet links** -- never set `addGoogleMeetUrl`/`googleMeetUrl`.
- **No default reminders** -- pass `overrideReminders: []`.
- **Distinct color from school events**: use colorId `9` (Blueberry) unless
  the user has said otherwise. School/academic events use colorId `10`
  (dark green) -- keep these visually separate. If the user wants a
  different color, that's a one-line ask, not a preference file (this skill
  has no persistent preference store of its own).
- **Description**: carry over the source event's own description text (if
  any, e.g. "Home Allocation") under a line like `Source: YMCA schedule`,
  plus the fingerprint tag (see below) appended at the end.
- **Location**: copy the source event's `location` field verbatim if
  present; don't invent one.

## Timing -- do not double-convert timezones

Source events carry explicit UTC instants (`dateTime` strings ending in
`Z`, e.g. `"2026-08-17T18:00:00Z"`), even though the calendar's own default
timezone is oddly set to UTC. When creating the mirrored event:

- Pass that same ISO 8601 string (with its `Z`/offset) directly as
  `startTime`/`endTime`.
- **Do not also pass a `timeZone` parameter** -- the tool schema says
  `timeZone` "overrides offsets in start_time/end_time," so setting it
  alongside an already-absolute UTC timestamp would silently shift the
  event by the offset difference. Let the absolute instant speak for
  itself; Google Calendar will render it correctly in the target
  calendar's own timezone (`America/Denver`) automatically.

## Idempotency -- this skill has no local database

Unlike `/academic-import`, there's no SQLite table backing this skill, so
Calendar-side state IS the only source of truth. Before creating anything:

1. Compute a short fingerprint tag for each source event:
   `[shift-sync:<source_event_id>]` (the source event's own `id` field is
   already stable and unique -- no hashing needed, just use it directly,
   e.g. `[shift-sync:_68o34dhd60s2qc9nbsojie1h6oo5uc0]`).
2. For the lookahead window, call
   `mcp__claude_ai_Google_Calendar__list_events` on the **target** (primary)
   calendar over the same date range, and check each returned event's
   `description` for a matching tag.
3. If a match exists and the title/start/end/location are unchanged: do
   nothing (already synced).
4. If a match exists but something changed (the source system moved the
   shift): call `update_event` with the new values, keeping the same tag.
5. If no match exists: call `create_event` with the tag embedded in the
   description.
6. If a previously-mirrored event's tag no longer corresponds to any event
   in the current source window (the shift disappeared from the source
   schedule): **do not delete it.** Tell the user: "Your mirrored shift
   '<title>' on <date> no longer appears in the YMCA schedule -- it may
   have been cancelled or moved. I left it on your calendar; let me know if
   you want it removed." This matches the same non-destructive rule
   `/academic-import` follows (see CLAUDE.md invariant 10) -- absence from
   a re-scan is not evidence of cancellation.

## Workflow

1. Determine the lookahead window: today through `$ARGUMENTS` days ahead
   (default 21).
2. `list_events` on the source calendar for that window.
3. `list_events` on the target (primary) calendar for the same window,
   collect existing `[shift-sync:...]` tags from descriptions.
4. For each source event: build the mirrored title/description/payload per
   the rules above, decide CREATE/UPDATE/UNCHANGED per the idempotency
   steps above, and act.
5. Check for tags present on the target but missing from the current source
   window -- report those per step 6 above, don't delete.
6. Summarize: N created, N updated, N unchanged, N flagged as possibly
   cancelled. Keep it to a few lines unless the user asks for the full list.

## Boundaries

- Never write to the source ("YMCA") calendar -- read-only, and the user's
  access to it is `reader` anyway.
- Never invite anyone or change sharing/permissions on either calendar.
- If the user asks to change the lookahead window, color, or title format
  as a lasting default, that's fine to just do directly in this skill (edit
  this file) since there's no separate preference mechanism for it yet --
  but confirm with the user before editing your own skill file.
