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

## Step 1 — Build the plan

Before any rotation begins, build an explicit cross-class teaching plan.
This is what actually replaces the Sweep's purely-reactive scoring: instead
of only ranking classes turn-to-turn, work out a real agenda across the
whole set up front.

For every active class, gather (all already-available data, no new Drive
schema):

- nearest upcoming deadline/exam and its `coverage_text` (Calendar Cache);
- whether the class has **zero** Quiz evidence anywhere this term (hard
  override — always most urgent regardless of the rest of the score);
- count of weak concepts (`review-weaknesses.md`'s Evidence Interpretation
  — confidence below 0, active review, or an active Signals-tab flag);
- whether the current week is untouched (`not started this week`).

Rank classes into three tiers:

1. **Urgent** — zero evidence anywhere, or a real deadline/exam inside the
   next few days with weak/untested coverage.
2. **Needs work** — weak concepts present, or current week untouched, no
   immediate deadline pressure.
3. **Retention** — everything currently at Working Mastery or better; no
   real gap, just keeping it warm.

Within each tier, order by the same signals the old Sweep used (nearest
deadline first, then weak-concept count, then untouched-this-week).

Show the plan as a real, visible agenda before rotation starts:

```markdown
## Mixed Study — Today's Plan

1. **BIO1112** — no study evidence yet and a quiz Friday. Starting here.
2. **MAT1340** — Chapter 2 untouched this week.
3. **CHE1011** — solid; retention pass to keep it warm.

Rotating through all three, weighted toward BIO1112 and MAT1340 until they catch up.

[K] Switch Class instead      [M] Menu / Save
```

This is computed live and **never persisted** — same treatment as
Complexity Tier and Curriculum Time Remaining (`startup-navigation.md`).
It is rebuilt fresh every time Mixed Study Mode is entered, including on
resume; only rotation *position* (below) is actually saved.

## Step 2 — Execute by rotation

Run one bounded "turn" per class per rotation cycle, in the plan's order:

- whatever Adaptive Study's normal per-concept routing (`adaptive-study.md`)
  would do next for that class's current highest-priority scope — one
  instructional lesson/chunk-and-comprehension cycle, or one 5-question
  Assessment batch;
- then move to the next class in the plan's order;
- after the last class in the plan, wrap back around to the first.

Announce each transition plainly, the same transparency the Sweep already
required: *"Moving to MAT1340 — Chapter 2 is still untouched."*

Urgent-tier classes get proportionally more turns per full cycle than
Needs-work, which get more than Retention — this is a weighting, not an
exclusion; every active class still gets turns.

## Step 3 — Rotation never exits once gaps close

Unlike the old Sweep, reaching Working Mastery across every class does not
end Mixed Study Mode. Once a class enters the Retention tier, it keeps
receiving turns — lower-frequency, but real — for spaced/interleaved
retention practice. This is what makes `[I]` usable as a sole, everyday
study driver rather than a mode that stops once "caught up."

The tier ranking from Step 1 is silently recomputed whenever a class's
state changes enough to move it between tiers (e.g. a class reaches
Working Mastery mid-session and moves from Needs-work to Retention) —
recompute the plan quietly, no need to re-announce the whole agenda unless
the ordering materially changes.

## Step 4 — Week-currency check at rotation boundaries

A long Mixed Study session can span real calendar days without the system
ever re-checking whether the date has rolled into a new week for any given
class. Rather than an arbitrary fixed number of questions, tie the check to
what's already a natural boundary: **at the moment a class receives the
next turn in rotation**, run that class's existing Refresh-Memory
week-rollover check (`startup-navigation.md`'s `[R]`, full mechanics owned
by `curriculum.md`) before continuing — bounded, narrow, same mechanics as
the manual version.

- **Match:** continue silently, no interruption.
- **Rollover found:** say so plainly the same way `[R]` normally does, and
  fold the new week's start-of-scope Foundational reach-back into that
  class's upcoming turn rather than treating it as a separate step.

This runs once per class per full rotation cycle by construction — no
separate timer or question counter needed. If a class ends up taking many
turns in a row (e.g. it's the only Urgent-tier class for a long stretch),
this check will run less often for it than for a class alternating every
turn; if that turns out to matter in practice, the fix is tightening this
to also fire after N turns within one class, not just at cross-class
boundaries — flagged here as an open tuning point, not implemented
speculatively.

## Navigation during Mixed Study

`[K]`, `[M]`, `[W]`, `[F]`, `[X]`, etc. behave identically to a
single-class session, scoped to whichever class currently has the turn.

`[M] Menu / Save` additionally saves **rotation position** — which class
was about to receive the next turn — the same last-write-wins way Teaching
-tab position is saved today (`drive-memory-schema.md`). On resume, Mixed
Study rebuilds the plan fresh (Step 1) but resumes rotation starting from
the saved class rather than always restarting at tier 1.

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
- A rotation boundary always re-checks that class's current week before
  teaching/quizzing continues.
- Per-class Quiz/Teaching/Reviews state was read and written through the
  same normal paths a single-class session would use — no shortcut writes.
