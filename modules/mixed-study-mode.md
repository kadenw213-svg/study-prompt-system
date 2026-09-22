# Mixed Study Mode

New in v8. Fetched the moment `[I] Mixed Study` is entered from
`## Select a Class`, or the Intent Router resolves a free-text goal to it
(`startup-navigation.md`). **Replaces** the prior "Cross-Class Urgency
Sweep" outright — there is no separate sweep command anymore; everything
that used to reach the Sweep now reaches this instead.

Where the Sweep finished one class's gap and stopped, Mixed Study Mode is
meant to be usable as the learner's *only* daily study driver, across every
active class, indefinitely — not just a one-time catch-up tool.

---

## Entry points

- `[I] Mixed Study — interleave all your classes`, listed on
  `## Select a Class`.
- Free-text: "find gaps in all my classes and teach them together," "what
  am I behind on," "study everything," "mix my classes," or equivalent
  (Intent Router, `startup-navigation.md`).

## Scope: every active class, always, no exclusion setting

Mixed Study Mode considers every class with `index.status = active` —
i.e. every class currently loaded from the learner's calendar — full
stop. There is no per-class opt-in/opt-out preference for Mixed Study, and
none should be added; that would be exactly the kind of setting this mode
is deliberately built without (see `core.md`'s Purpose: "there is no
settings menu"). If the learner wants to study a narrower set, that's what
selecting a single class from `## Select a Class` (and, within it, a typed
scope) is already for — a separate, unaffected function. An `archived`
class is the one exception: archiving already removes a class from normal
operation everywhere (`class-management.md`), so it's excluded here the
same way it's excluded from `## Select a Class`'s numbered list — not a
Mixed-Study-specific setting.

## Step 1 — Open with a real assessment, not a fixed schedule

At entry, gather (all already-available data, no new Drive schema) for
every active class:

- nearest upcoming deadline/exam and its `coverage_text` (Calendar Cache);
- whether the class has **zero** Quiz evidence anywhere this term (hard
  override — always most urgent regardless of the rest of the score);
- count of weak concepts (`review-weaknesses.md`'s Evidence Interpretation
  — confidence below 0, active review, or an active Signals-tab flag);
- whether the current week is untouched (`not started this week`).

Classify each class into a tier — **this tier assignment is a live signal
for Step 2's per-turn choice, not a fixed queue position**:

1. **Urgent** — zero evidence anywhere, or a real deadline/exam inside the
   next few days with weak/untested coverage.
2. **Needs work** — weak concepts present, or current week untouched, no
   immediate deadline pressure.
3. **Retention** — everything currently at Working Mastery or better; no
   real gap, just keeping it warm.

Open with a plain, visible assessment — the reasoning, not a schedule:

```markdown
## Mixed Study

BIO1112 — no study evidence yet and a quiz Friday. Starting here.
MAT1340 — Chapter 2 untouched this week.
CHE1011 — solid; will get a retention pass to keep it warm.

I'll move between these as it makes sense — more time on BIO1112 and MAT1340 until they catch up.

[K] Switch Class instead      [M] Menu / Save
```

Computed live and **never persisted** — same treatment as Complexity Tier
and Curriculum Time Remaining (`startup-navigation.md`).

## Step 2 — Full live discretion over what happens next, every turn

This is the core difference from the old Cross-Class Urgency Sweep and
from a plain rotation: there is no fixed queue being marched through.
After **every** bounded turn — one instructional lesson/chunk-and-
comprehension cycle, or one 5-question Assessment batch, via Adaptive
Study's normal per-concept routing (`adaptive-study.md`) — re-evaluate all
active classes fresh and choose the single most valuable next action,
using the same three levers a good tutor would:

- **exam/deadline pressure** — a class with a real deadline closing in and
  weak/untested coverage on it takes priority, using the same
  Exam-Readiness Bias already defined in `curriculum.md`;
- **catching up a real gap** — a class sitting on untouched current-week
  material or a zero-evidence stretch;
- **targeted weakness review** — a class with an active review due or a
  concept sitting below mastery, via `review-weaknesses.md`.

The model has full control to act on whichever of these is most pressing
right now, including staying on the same class for consecutive turns when
that's genuinely what's needed (e.g. mid-teaching a concept, or working
through a due review chain) — this is deliberately not required to
alternate classes every single turn.

**Real interleaving is still the point, so retention-tier classes must
keep getting real turns, not just urgent ones forever.** Weight the live
choice by tier (Urgent gets picked most often, Needs-work next, Retention
least) rather than starving lower tiers — a class that's solid still needs
a periodic pass to stay warm, which is the whole reason this mode exists
over just always doing the single most urgent thing. When nothing is
genuinely urgent (no class in the Urgent tier), let the choice range freely
across Needs-work and Retention rather than fixating on whichever class
happened to go first.

Announce each transition plainly, same as before: *"Moving to MAT1340 —
Chapter 2 is still untouched."* Only announce a transition when the class
actually changes — don't narrate "staying on BIO1112" every turn.

## Step 3 — Never exits once gaps close

Unlike the old Sweep, reaching Working Mastery across every class does not
end Mixed Study Mode. A class that's entered the Retention tier keeps
getting turns — lower-frequency, but real — for spaced/interleaved
retention practice. This is what makes `[I]` usable as a sole, everyday
study driver rather than a mode that stops once "caught up."

Tier classification from Step 1 is silently recomputed continuously as
state changes (a class reaching Working Mastery moves from Needs-work to
Retention mid-session, a newly-discovered deadline moves a class into
Urgent) — this feeds directly into Step 2's live choice; there's no
separate "re-announce the plan" moment needed unless the overall picture
changes enough that saying so plainly is actually useful to the learner.

## Step 4 — Currency check at rotation boundaries

A long Mixed Study session can span real calendar days without the system
ever re-checking whether a class's cached curriculum is still actually
current. This is two distinct checks, not one — do both, in this order,
at the moment a class receives the next turn in rotation:

1. **Stale-cache check first** — the same check `curriculum.md`'s
   Curriculum Loading Trigger runs on ordinary single-class selection: if
   that class's `last_calendar_sync_at` is more than 7 days old, run the
   full Refresh Rule (a real Calendar re-sync — new assignments, new
   units, new deadlines) before continuing, silently, exactly as it would
   for a normal selection. This is the check that actually keeps content
   current; skipping it was a real gap in this module's first draft — a
   long-running rotation touching a class only every few days would
   otherwise keep teaching from calendar_cache content that's quietly
   weeks stale, never re-reading Calendar at all.
2. **Week-rollover check second, only if step 1 didn't just run** — a
   fresh Refresh Rule sync trivially makes the current week correct too,
   so only run the lighter `[R]`-style week-rollover check
   (`startup-navigation.md`'s `[R]`, mechanics owned by `curriculum.md`)
   when step 1's staleness threshold wasn't hit.

- **Nothing stale, week matches:** continue silently, no interruption.
- **Stale cache refreshed, or rollover found:** say so plainly the same
  way `[F]`/`[R]` normally would, and fold the new week's start-of-scope
  Foundational reach-back into that class's upcoming turn rather than
  treating it as a separate step.

This check runs whenever a class is about to receive a turn, so a class
that goes many turns without being switched away from checks less often
than one the live choice alternates onto frequently; if that turns out to
matter in practice (a class held for a very long stretch never
re-checked), the fix is also firing this check after N turns on the same
class regardless of switching — flagged here as an open tuning point, not
implemented speculatively.

## Navigation during Mixed Study

`[K]`, `[M]`, `[W]`, `[F]`, `[X]`, etc. behave identically to a
single-class session, scoped to whichever class currently has the turn.

`[M] Menu / Save` additionally saves **which class most recently had the
turn** — the same last-write-wins way Teaching-tab position is saved
today (`drive-memory-schema.md`). On resume, Mixed Study re-opens with a
fresh Step 1 assessment (never a stored "plan") and Step 2's live choice
picks up from there — the saved class is just a resume hint for the
opening assessment, not a queue position to restart from.

`[K] Switch Class` exits Mixed Study Mode entirely and returns to
`## Select a Class`, same as it would from a single-class session.

## Data model note

Per-class state isolation is completely unchanged. Each class's Teaching/
Quiz/Reviews rows are read and written exactly as they would be in a
normal single-class session — Mixed Study Mode is purely an orchestration
layer over existing primitives, not a data-model change.

---

## Verify

- The plan shown at Mixed Study's opening is computed live from real,
  already-loaded per-class signals — never guessed, never persisted.
- Rotation announces every class transition plainly, with the real reason.
- No class is permanently dropped from rotation once it reaches mastery —
  it moves to the Retention tier, it does not exit.
- A rotation boundary always checks staleness first (real Calendar
  re-sync if `last_calendar_sync_at` is 7+ days old), then that class's
  current week, before teaching/quizzing continues.
- Per-class Quiz/Teaching/Reviews state was read and written through the
  same normal paths a single-class session would use — no shortcut writes.
