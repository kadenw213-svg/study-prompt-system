---
name: daily-overview
description: Every-morning (5am, unattended via Windows Task Scheduler) check of each real D2L course -- new announcements, newly graded work and instructor feedback, missed and due-today deadlines -- sent as one "Daily Overview <CODE>" email per course, plus small Calendar upkeep. Use when the user asks to run, test, or fix their daily overview / morning email, or when invoked headless by scripts/daily_overview.ps1.
user-invocable: true
---

# /daily-overview -- the course shell, relayed by email

Arguments passed: `$ARGUMENTS` (may be empty, a course code, or `--date
YYYY-MM-DD` for a manual re-run of a specific day).

The goal (user-directed 2026-10-05): **the user never has to open a course
shell to find out what changed.** Each morning, every real course is
checked, and anything new arrives as one email per course, with every item
linked straight to the page where they act on it. Read CLAUDE.md first,
especially invariants 1, 23, 30, 37, 38 and 39.

**This usually runs unattended.** `scripts/daily_overview.ps1` starts it
headless at 5:00am (`claude -p "/daily-overview" --chrome`). Nobody is
watching. Never stop to ask a question. When something can't be resolved,
put it under "Needs you" in that course's email and keep going.

**Working directory:** repo root. All local work goes through `uv run
academic-sync ...`.

**Live tools:** Chrome (`claude-in-chrome`) for D2L and external platforms;
Gmail `send_message` (to the `digest_email_to` preference only); Google
Calendar for upkeep; Drive search/read plus the browser for the Sheets
signal write.

## What the email contains, and what it never contains

Built by `digest-render` (`src/academic_sync/sync/email_payload.py`). Don't
hand-write the HTML. Subject: `Daily Overview <CODE>`. In order:

1. **Current grade** in bold at the top, with its trend since about a week
   ago.
2. **Needs attention.** Only *new* triggers: a real zero, a major
   assessment under 60%, 2+ missing items, or a 10+ point weekly drop.
   Each is reported once, not every morning.
3. **Newly graded.** Each item gets its link, the exact score as D2L shows
   it, the instructor's comment **verbatim**, and an "Open feedback" link.
4. **New announcements.** Title, link, and short **verbatim** excerpts.
5. **Missed yesterday.** Each one says whether it's still open (with a
   submit link) or closed.
6. **Due today**, plus **Coming up** for the next 3 days as context.
7. **Calendar updated** (what this run changed) and **Needs you**.
8. A footer of the course's portal links.

**No readings.** The weekly banner is the reading list. **No email on a
quiet day.** No email for synthetic (self-study) courses. Advice
(`advice` in the crawl JSON) is optional, clearly labeled, written by you,
and only given when the grade moved or new work was graded. Never repeat
the same grade warning daily.

## Step 0: orient (fast)

1. `uv run academic-sync courses`. In scope: every `active`, non-synthetic
   course (or just `$ARGUMENTS`' course).
2. `uv run academic-sync prefs get digest_email_to`. If unset, still crawl
   and ingest, but nothing can send. Say so in the run's output.
3. `uv run academic-sync portal-link-list --course <CODE> --json` per
   course. **If a course is missing its core links** (home, grades,
   announcements, content, dropbox, quizzes, and the external gradebook for
   any external platform), discover them once:
   - Open each area from the course's own navbar and save the URL that
     actually loaded with `portal-link-set --course <CODE> --kind <kind>
     --url "<url>" [--label "..."]`.
   - Save only a URL you opened and saw load the right page (invariant 38).
   - From then on, navigate straight to saved links; don't click through
     the shell.

## Step 1: log in (invariant 39)

1. Open the `d2l_base_url` preference.
2. If it lands on the D2L homepage, you're logged in.
3. If it redirects to the institution's SSO sign-in page (the host in
   `config/personal.local.md`'s `sso_host` -- check that the page you're
   on matches it), the user has authorized you to click **Sign In** when
   the username and password fields are already filled (by Chrome or
   LastPass).
   - If the fields are empty, click the password manager's in-field icon
     once (LastPass), wait about 5 seconds, and check again.
   - **Never type, read out, copy, or store the password.** Never sign in
     anywhere except that SSO page.
4. Still not in? That includes empty fields, an MFA or CAPTCHA prompt, an
   error, or an unfamiliar page. Then the run continues with
   `login_failed: true` for every course. The email still goes out, built
   from local deadlines, with a visible "D2L login failed" warning.

## Step 2: crawl each course (bounded: aim for no more than about 10 page loads per course)

Use D2L's REST API through in-page `fetch` from the logged-in tab
(`javascript_tool`). It returns structured JSON in one call per area, the
same technique as the content TOC API in `docs/d2l_discovery.md`. Find the
versions first with `fetch('/d2l/api/versions/')` and use the newest
`le`/`lp`.

- **Announcements:** `GET /d2l/api/le/<v>/<ou>/news/`.
  - `id` = the news item Id.
  - `title`, `posted_on`.
  - `highlights` = 1–4 short verbatim excerpts. Always include any
    sentence that states a date, deadline, room change, or "submit"
    instruction.
  - `url` = that announcement's own page, or the saved announcements
    link.
- **Grades:** `GET /d2l/api/le/<v>/<ou>/grades/values/myGradeValues/` for
  items, and `.../grades/final/values/myGradeValue` for the overall grade.
  - `id` = grade object id.
  - `score_text` exactly as displayed, e.g. "36 / 50", plus
    `score_percent`.
  - `comment` = the Comments text verbatim; omit it if empty.
  - `graded_on` from the last-modified date when present.
  - `item_url` = the item's own page (from the local item's
    `reference_url` when the titles match).
  - `feedback_url` = the page where that feedback is read: the Dropbox
    "View Feedback" page for dropbox items, otherwise the saved grades
    link.
  - `is_major` and `chapter_label` come from the matching local item
    (exam, final or project type; its module/chapter). If you can't match
    one, leave them unset.
- **External platforms** (ALEKS, Connect, ...): open the saved
  `external_gradebook` link and read its **gradebook**, never the
  dashboard (invariant 23). Add those scores to `grades`, with
  `id = "<platform>:<item name>"`.
- **Deadline status:** run `uv run academic-sync digest-deadlines --course
  <CODE>`. For each `yesterday`/`today` item, check whether it was
  submitted: a dropbox submission, a quiz attempt, or a platform gradebook
  status.
  - Report `submitted` true/false/null (null = couldn't confirm).
  - Report `window_open`: does the folder or quiz still accept a
    submission now?
  - Set `missing_count` from D2L's or the platform's own missing count
    when it shows one.
- **Calendar upkeep (small, same rules as `/academic-sync`):**
  - If a new announcement states a new or changed date, run it through
    `extract` (source type `d2l_announcements`), then `plan`. Push only
    CLEAR CREATE/UPDATE entries via `render` → `create_event`/
    `update_event` → `record-sync`.
  - Run `uv run academic-sync needs-link-refresh --course <CODE>` and fill
    any newly unlocked links (`render --reference-url ... --save`, then
    `update_event`).
  - Every change you make becomes a `calendar_changes` line, with a link
    where one exists.
  - Anything ambiguous or conflicting, or anything that would take a big
    crawl, becomes a `needs_you` line, not a guess (invariants 1, 9, 34).

## Step 3: ingest

1. Write the crawl to `data/digests/<CODE>/<YYYY-MM-DD>.json`, matching
   `digest.DigestCrawl`:
   ```json
   {"course": "MAT1340", "captured_on": "2026-10-06", "login_failed": false,
    "overall_percent": 43.1, "letter_grade": "F", "missing_count": 0,
    "announcements": [{"id": "...", "title": "...", "posted_on": "2026-10-05",
                       "url": "...", "highlights": ["verbatim ..."]}],
    "grades": [{"id": "...", "title": "...", "score_percent": 72, "score_text": "36 / 50",
                "comment": "verbatim ...", "item_url": "...", "feedback_url": "...",
                "graded_on": "2026-10-05", "is_major": true, "chapter_label": "Chapter 3"}],
    "deadline_status": [{"item_id": "...", "submitted": false, "window_open": true}],
    "calendar_changes": [{"text": "Added Exam 3 (Oct 20)", "url": "..."}],
    "needs_you": [{"text": "...", "url": "..."}],
    "advice": null}
   ```
   Always include every current announcement and grade you saw. Dedupe is
   automatic: anything already emailed with unchanged content is never
   re-sent, and a regrade or new feedback resurfaces as "updated". On a
   course's very first run, older history is baselined automatically.
2. Run `uv run academic-sync digest-ingest --file <path>`. It prints counts
   and `signal_candidates`.
3. For each signal candidate (a major assessment newly under 60%, tied to a
   real chapter), write a weakness signal to the quiz system's Drive
   workbook, following `/academic-sync`'s **Drive weakness signal**
   section. If that browser write fails while unattended, add a
   `needs_you` line instead.

## Step 4: render and send

1. Run `uv run academic-sync digest-render --course <CODE>`.
2. If `should_send` is true, call `send_message`:
   - `to`: the printed `to`
   - `subject`: the printed `subject`
   - `htmlBody`: the printed `html`, verbatim
   - `body`: the printed `text`
   Then record it: `uv run academic-sync digest-record-sent --course <CODE>
   --message-id <id from the send result>`.
3. If `has_news` is false (a quiet day), run `digest-record-sent --course
   <CODE> --skipped`.
4. If `already_sent` is true, do nothing. Re-running a morning never
   double-sends.
5. Send only to `digest_email_to`, from the connected account. Never add
   cc or bcc, and never send to anyone else.

## After running

Print one line per course: sent / skipped (quiet) / login failed / error.
When headless, this goes to `data/logs/daily_overview_<date>.log`.

## Rules (CLAUDE.md is authoritative)

- Scores, comments, announcement text, and dates are copied verbatim from
  the real page. Never paraphrase them into something they didn't say,
  and never invent them.
- Never fabricate a date or link. Calendar writes follow every existing
  invariant: no guests, no Meet links, idempotent.
- One email per course per day.
- If you're about to hand-write dedupe, trend math, or email HTML, stop.
  That's `digest.py` / `email_payload.py`.
