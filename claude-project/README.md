# academic-sync

A local-first pipeline that turns your D2L/Brightspace course material into a
structured, evidence-backed model of your academic obligations, and syncs the
*clear* subset into your Google Calendar -- safely, repeatably, without
duplicating events.

It does not try to guess what it can't see. A detailed syllabus is not treated
as a complete picture of a course; if the syllabus says "see D2L for lab
schedule," the system tracks that as an open question until someone (you, via
the import skill) actually looks at the D2L lab schedule.

## How this is built

This project deliberately does **not** reimplement Google OAuth or browser
automation. It runs as two Claude Code skills:

- **`academic-import`** -- drives D2L discovery live, through your own logged-in
  Chrome session (via Claude Code's browser control) and writes to your Google
  Calendar through Claude Code's already-authorized Google Calendar connector.
  No separate OAuth client, no stored password, no persisted browser session
  file.
- **`academic-prefs`** -- inspects/edits your saved preferences (target
  calendar, colors, default due time, room mappings, precedence rules, etc).

Underneath both skills is a real, independently testable Python package
(`src/academic_sync/`) that does all the deterministic work: HTML/PDF parsing,
date extraction, completeness analysis, deduplication/reconciliation, and
local persistence (SQLite). Claude does the parts that require live web
interaction and judgment calls (which document to open, which sync plan items
look right); the Python package does the parts that must be deterministic and
testable (date math, fingerprinting, idempotency).

See `docs/architecture.md` for the full design and `CLAUDE.md` for the
non-negotiable invariants a future engineering session must not violate.

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- Claude Code, with:
  - Chrome browser control enabled (`claude-in-chrome`) for D2L access
  - The Google Calendar connector authorized against the Google account you
    want events written to

You do **not** need a Google Cloud project, an OAuth client, or Playwright.
Those were part of an earlier standalone-app design; this project intentionally
piggybacks on tools Claude Code already has, which removes an entire class of
credential-management work. If you later want a headless, Claude-independent
scheduled job, see "Standalone mode" in `docs/architecture.md` for what would
need to be added.

## Installation

```bash
uv sync --extra dev
```

This creates `.venv/` and installs the `academic_sync` package plus test/lint
tooling. The CLI entry point is `academic-sync` (or `uv run academic-sync`).

Initialize the local database:

```bash
uv run academic-sync db init
```

This creates `data/academic_sync.db` (SQLite, gitignored) and applies all
schema migrations. Safe to re-run.

## Google Calendar

Nothing to configure here beyond confirming the target calendar and color,
which are stored as preferences (see below). Calendar writes happen when you
run the `academic-import` skill's sync step; the skill uses Claude Code's
Google Calendar connector directly, so there's no `.env` key or OAuth consent
screen for this project.

Defaults (overridable via `academic-sync prefs set`):

| Preference | Default |
|---|---|
| target calendar | your primary calendar |
| event color | colorId `10` (dark green) |
| default reminders | off |
| guests invited | never |
| Google Meet links | never created |
| timezone | `America/Denver` |
| default due time (date-only sources) | `23:59` |

## D2L / Brightspace

There's no API credential to configure. The `academic-import` skill opens
your D2L pages through your own authenticated browser session, the same way
you'd browse them yourself. When it needs your institution's login page, it
will show you the page and wait for you to log in (including any MFA step) --
it never touches your password.

The first time you run the import skill, tell it your D2L base URL /
institution's login portal. It's saved as a preference
(`d2l.base_url`) so you won't have to repeat it.

## First run

```
1. uv run academic-sync db init
2. In Claude Code: run the academic-import skill and tell it which term/courses to scan
   -> it will log you into D2L interactively, crawl each course, download syllabi/handouts,
      and run them through the extraction + completeness pipeline
3. Review the completeness report it shows you (COMPLETE / COMPLETE_FOR_DATED_ITEMS /
   INCOMPLETE / CONFLICTED / UNKNOWN, per course)
4. Review the unresolved-items queue -- these are things the system deliberately
   would NOT guess at
5. It shows you a dry-run sync plan: CREATE / UPDATE / UNCHANGED / CONFLICT / REVIEW,
   grouped by course
6. Approve the plan (or a subset of it) to apply it to your Google Calendar
```

Re-running the import skill later is safe -- it will not create duplicate
events. It compares fingerprints, not just titles, so a changed due date
becomes an UPDATE, not a second event.

## CLI reference

The CLI is the deterministic half of the system -- it operates on already-
downloaded/extracted content and the local database. It does not talk to D2L
or Google on its own; the skills call into it.

```bash
uv run academic-sync db init                     # create/upgrade local database
uv run academic-sync courses                      # list known courses
uv run academic-sync extract <path> --course ID --source-type syllabus
                                                   # run the extraction pipeline over one file
uv run academic-sync completeness [--course ID]    # print completeness report(s)
uv run academic-sync unresolved [--course ID]      # list open UnresolvedReference items
uv run academic-sync unresolved-add --course ID --description "..." [--kind KIND] [--source-wording "..."]
                                                   # record a live discovery finding (e.g. a
                                                   # courseware link off the LMS's own domain
                                                   # not yet opened) that the deterministic
                                                   # pipeline can't see on its own
uv run academic-sync unresolved-resolve REF_ID --note "..."
                                                   # manually clear one (auto-clears on its own
                                                   # once a matching Source is added -- see
                                                   # CLAUDE.md invariant 20)
uv run academic-sync plan [--course ID]            # compute CREATE/UPDATE/UNCHANGED/... sync plan
uv run academic-sync audit [--limit N]             # tail the audit log
uv run academic-sync status                        # one-screen summary across all courses
uv run academic-sync prefs list
uv run academic-sync prefs set <key> <value> [--course ID]
uv run academic-sync prefs get <key> [--course ID]
uv run academic-sync prefs unset <key> [--course ID]
```

`plan` never writes to Google Calendar -- it only computes and prints the plan
using locally stored sync-record fingerprints. Actually applying a plan (real
Calendar writes) is done by the `academic-import` skill, which calls Claude's
Google Calendar connector for each planned CREATE/UPDATE and then records the
result via `academic-sync record-sync` (see `docs/architecture.md`).

## Preference management

```bash
uv run academic-sync prefs list
uv run academic-sync prefs set default_due_time 23:59
uv run academic-sync prefs set target_calendar_id primary
uv run academic-sync prefs set room_mapping.BIO1112 "Centennial Hall, Room 204" --course BIO1112
```

Preferences are never inferred from a casual mention in a syllabus -- only
set here, explicitly, or confirmed by you when the import skill asks
("I found two rooms and can't tell which is lecture vs lab -- which is which?").
Course-scoped preferences (`--course ID`) override global ones for that course.

## Troubleshooting

- **"No courses found"**: run the import skill again and confirm you're
  logged into D2L in the Chrome tab it opened -- SSO sessions expire.
- **Completeness stuck at `UNKNOWN`**: means no sources have been scanned yet
  for that course. Run a scan.
- **An item never leaves the unresolved queue**: check
  `academic-sync unresolved --course ID` for the reason; it always records
  *why* something wasn't auto-resolved (missing date, ambiguous room, etc).
  Resolve it by supplying the missing fact as a preference, or by pointing the
  import skill at the source that actually has the answer.
- **Duplicate-looking events**: shouldn't happen through this system, but if
  you manually created something with a similar title, the reconciliation
  engine compares fingerprints, not titles -- it will not merge or dedupe
  against events it didn't create itself. Check `academic-sync plan` output;
  a CREATE for something you think already exists usually means the existing
  event has no matching fingerprint (i.e. this tool didn't create it).

## Scheduled runs

Because D2L login may require MFA, a fully unattended background sync isn't
safe to build blindly. The practical model is: schedule a reminder (Claude
Code's own scheduler, Task Scheduler, cron, whatever you use) to run the
import skill periodically with you present for the few seconds an SSO session
needs; the skill's change-detection (content hashing) means most runs will be
fast no-ops. See `docs/architecture.md` for the incremental-scan design.

## Privacy & security

See `docs/security.md`. Short version: your D2L password is never seen or
stored by this system (you log in through your own browser); course documents
never leave your machine unless you explicitly enable the optional LLM
extraction adapter (off by default); the local SQLite database and any
downloaded course files are gitignored.
