# Style guide -- the narrator's voice and the evidentiary bar

## Voice: witty and literary, never a real person's likeness

Write scripts to be read by an **original synthetic voice** (Kokoro's own
stock `am_fenrir` voice by default -- a deep, dry, deliberate voice well
suited to long-form narration). This project deliberately never attempts
to clone a real, identifiable person's actual recorded voice, including
via voice-conversion tooling trained on real audio samples of them -- that
line was drawn explicitly during this skill's design and is not revisited
by a future session without the user explicitly re-opening it.

What's fair game is the *rhetorical style* of the scripts you write, which
is deliberately modeled on Christopher Hitchens' public speaking/essay
voice: erudite, confident, argumentative, willing to take a position and
defend it, dry wit, well-turned and slightly long sentences that build to
a point, occasional historical/literary allusion when it actually
illuminates the material (not decoration for its own sake), a willingness
to editorialize about why a topic matters or where the received wisdom is
thin -- while never inventing or distorting the actual academic content
underneath it. **Style is free; facts are not.**

## Structure (per lecture, i.e. per WEEKLY_READING unit)

1. **Cold open** -- one or two sentences framing why this week's material
   matters or what's counterintuitive about it. Not "Today we'll
   cover..." -- start mid-thought, like a real essay opening.
2. **Roadmap** -- a brief, confident statement of what the week covers,
   drawn straight from the unit's real `chapter_blocks`.
3. **Body, one block per real chapter/topic** -- for each `ChapterBlock`
   with captured vocabulary/objectives, work through them as connected
   prose, not a read-aloud bullet list: explain what each
   objective/vocabulary term means and why it matters, with real
   transitions between chapters (not "moving on to..."). For a
   `ChapterBlock` with only a bare label (no captured `ChapterTopic` yet),
   say what little is known plainly and move on -- do not pad it with
   invented specifics.
4. **Digressions are welcome** when they serve understanding (a relevant
   historical anecdote, a real-world analogy) -- keep them clearly
   illustrative, never presented as if they were part of the graded
   material itself.
5. **Closing synthesis** -- tie the week back to the course's larger arc;
   end on a real point, not a restated summary.

## The evidentiary bar (CLAUDE.md invariant 22, generalized to audio)

Every substantive factual claim about *what the course covers* must trace
to one of:

- a saved `ChapterTopic.vocabulary`/`objectives` for that chapter (the
  richest case), or
- the unit's real `module_label`/chapter label text (thinner, but real), or
- a real `weekly_links` resource (only describe what a linked slide
  deck/video covers if you've actually looked at it).

For a **real, non-synthetic course**, never generate plausible-sounding
chapter content that isn't backed by one of the above -- same bar as any
other academic-sync output. If a unit is thin, tell the user it's thin
(and that richer narration needs `academic-import`'s `chapter-topic-add`
step run first) rather than inventing depth to make a better-sounding
lecture.

For a **synthetic (`custom-curriculum`) course**, `Course.is_synthetic`
already means *you* are the authoring source (CLAUDE.md invariant 35) --
write the real depth directly, no separate citation needed.

## Length

Aim for a genuinely full lecture per week -- dense enough to run 20-45
real minutes, not a 3-minute highlight reel. Use everything the unit's
`chapter_blocks`/`weekly_links` actually support; a week with rich
captured vocabulary/objectives can and should run long. A week with only a
bare chapter label stays short -- thin source, thin lecture, never padded
to hit a length target.

## Mechanical checks (already run for you)

`audio-lectures synthesize` calls `script_writer.validate_script` before
rendering and prints warnings for scripts under ~250 words (looks
incomplete) and leftover placeholder text (`TBD`, `[insert ...]`, etc.).
Treat any warning as something to fix, not something to synthesize anyway.
