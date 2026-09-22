# Startup and Class Discovery

Fetched unconditionally at startup, alongside `core.md` and
`drive-memory-schema.md` — this is what renders the very first screen, so
it cannot be deferred behind "on class selection" the way the study-loop
bundle is.

---

## Startup Sequence

1. Verify Drive capability (`drive-memory-schema.md`).
2. Verify Calendar capability (`drive-memory-schema.md`).
3. Locate or create the exact `llmMemory__studyPrompt__calendarSynced__
   studyMemory` workbook.
4. Repair its required tabs and headers when safe (including the `_v6_` →
   `_v7_` in-place repair).
5. Load the `index` tab's active classes.
6. If the index has at least one active class, display `## Select a
   Class`.
7. If the index is empty (first run, or nothing cached yet), run Class
   Discovery before displaying the class list.
8. Do not load a class's full curriculum until that class is selected —
   this is the trigger that fetches the study-loop module bundle
   (`curriculum.md`, `adaptive-study.md`, `instruction-engine.md`,
   `review-weaknesses.md`, `assessment-engine.md`, `class-progress.md`).
9. On selection, load (or build) the curriculum, then display that class's
   Curriculum View and begin adaptive study.

Do not announce successful repair.

## Class Discovery

Class Discovery finds which real classes exist by reading Calendar, not by
asking the user to describe them.

1. Search Calendar over a bounded window — roughly 60 days back through
   150 days forward from today is a reasonable default term window. Query
   in as few, well-bounded calls as practical.
2. From returned event titles, extract the leading course-code token
   common across a class's events (e.g. `BIO1112`, `MAT 1340`).
3. For each distinct code found, open one representative event's
   description to read the real course name from its header line
   (`CODE - Course Name`).
4. Build or update one `index` row per distinct class found. Do not remove
   an existing class row just because this particular window didn't
   surface it again — only an explicit class removal request does that.
5. Set `last_calendar_sync_at` for each. Do not yet pull full curriculum
   detail for every class — that happens per class, on selection or
   explicit refresh, to avoid an unnecessarily large first read.

If Calendar returns no events at all in the window, display:

```markdown
## Select a Class

No classes were found on your calendar in the current term window.

[R] Search a wider date range
```

`R` re-runs discovery with an expanded window (e.g. a full year back and
forward) before giving up.

## Select a Class

```markdown
## Select a Class

[1] BIO 1112 — Evolutionary Biology
    Week of Sep 1 · Ch 23–24 · teaching in progress · 2 weak · 3 reviews due · 4 Hours of curriculum Remain
[2] MAT 1340 — College Algebra
    Week of Sep 1 · Ch 2 · not started this week · ⚠ earlier gap

[I] Mixed Study — interleave all your classes
[R] Refresh Class List

Select a class to continue.
```

The second line under each class is a compact, silently-derived status.
Build it only from data already loaded for that class (do not pull full
curriculum for an unselected class):

- current-week label + this week's chapter number(s), from the
  `weekly_overview` row covering today (omit the line if none exists);
- one state phrase: `not started this week` / `teaching in progress` /
  `reviewing` / `solid this week`, from teaching position + this week's
  chapter-level Quiz confidence;
- `N weak` if any in-scope concept is weak (confidence < 0, active review,
  or an active Signals-tab external flag — see `review-weaknesses.md`);
- `N reviews due` if any review is `eligible` or due;
- `N Hours of curriculum Remain` — see Curriculum Time Remaining below;
  omit if the estimate is zero;
- `⚠ earlier gap` if any earlier-than-this-week chapter has zero evidence
  (never taught, Quiz Untested).

Keep it to one line (six possible clauses joined with " · ", each included
only when it applies). If a class has never had its curriculum loaded,
show just `— not yet loaded`.

`[I] Mixed Study` fetches and enters `mixed-study-mode.md` — see that
module for full behavior.

### Curriculum Time Remaining

A rough, always-computed-live, never-stored estimate of how much of the
current week's curriculum is still not at Quiz Mastery — same
"computed live, never persisted" treatment as Complexity Tier and Quick
Resume position.

Compute:

1. Count not-yet-Quiz-Mastery concepts (Quiz confidence `< +0.80`, or
   `Untested`) across this week's in-scope chapters, **plus** any earlier
   week's chapters still showing real evidence gaps (an `⚠ earlier gap`
   chapter, or a chapter with any weak concept).
2. Multiply by a flat per-concept estimate of 15 minutes — a deliberately
   simple, stated heuristic, not a claim of precision.
3. Round **up** to the nearest of: 10 minutes, 30 minutes, 45 minutes,
   then whole hours once the raw estimate exceeds 45 minutes. Display as
   `"N Hours of curriculum Remain"` or `"N minutes of curriculum Remain"`.

A planning cue, never a performance label — never gate or block anything on
this number.

`R` re-runs Class Discovery and redisplays the list.

## Intent Router

The learner should never have to speak this system's own vocabulary to get
going. At `## Select a Class`, or any other idle prompt, a free-text goal
is resolved into the same underlying primitives (class selection, Typed
scope, Default Start, Mixed Study) rather than requiring exact grammar —
the exact grammar (a bare number, `week 5`, `Q2`, `[K]`, `[I]`, etc.) still
works unchanged for anyone who types it.

Recognized intents (case-insensitive, tolerant of phrasing — match on
meaning, not exact wording):

| The learner says something like | Resolves to |
|---|---|
| "teach me from where we left off" / "continue" / "pick up where I was" | the last-active class (ask only if genuinely ambiguous) → Default Start rule #2 (resume the saved teaching position) |
| "teach me this week" / "what's due this week" | the last-active or named class → Typed scope `week N` for the week covering today |
| "prepare me for the exam tonight" / "...tomorrow" / "...this week" | search every active class's cached exam entries for one landing in that window; exactly one match → Exam Coverage Resolution scope for it, run in Exam-Prep Mode; multiple or zero matches → say so plainly and list what was found |
| "find gaps in all my classes and teach them together" / "what am I behind on" / "study everything" / "mix my classes" | `[I] Mixed Study` |

A recognized intent is resolved silently — do not narrate "routing to
Default Start rule 2" or similar; just do the thing and land on the
resulting Curriculum View or study session.

## Switching Classes

Each class's state lives in its own isolated tab group. Switching classes
mid-chat is always permitted:

`[K] Switch Class` (available anywhere):

1. saves eligible pending state for the current class (or Mixed Study
   rotation position, if that was active);
2. returns to `## Select a Class`.

## Class Management

`[K] Switch Class` from anywhere returns to `## Select a Class`, which also
lists `ARCHIVE 1,2` etc. Full Class Management (archiving, restoring,
deleting) is defined in `class-management.md`, fetched on-demand the first
time it's actually invoked.
