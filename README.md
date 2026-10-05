# Study Prompt System

An exam-prep quizzer for ChatGPT. You study from the real readings linked on your Google Calendar's weekly overviews. This system checks that it stuck: pick a class, and it gives you **10 exam-style questions** over everything covered so far, grades all 10 at once, explains only the ones you missed (each with a link back to the reading), and tracks your weak spots across sessions in one Google Drive spreadsheet. It never makes up course content and never edits your calendar.

This repo has two halves:

- **The quiz system** (`boot.md`, `engine/`, `ops/`) runs in ChatGPT.
- **`claude-project/`** is the Claude Code project that scans your classes from D2L into Google Calendar (the weekly overviews this quiz system reads), sends a daily per-class email of what changed, and includes related tools.

---

## Start a quiz (ChatGPT)

**One-time setup**

1. In ChatGPT **Settings → Plugins/Connectors**, connect **GitHub**, **Google Drive**, and **Google Calendar**.
2. Use a normal chat, not a Custom GPT (Custom GPTs can't reach Drive and Calendar).

**Every session**: open a new chat and paste:

```text
You are an exam-prep quiz system. Use the GitHub connector to open https://raw.githubusercontent.com/kadenw213-svg/study-prompt-system/main/boot.md, read it fully, and follow it exactly. Don't explain or summarize it — just start.
```

## Using it

| You do | It does |
|---|---|
| Pick a class number | Shows what's covered so far and when your next exam is, then gives you a set of 10 questions. |
| Answer all 10 in one message: `1 B` · `2 A,C` · `3 4.20 mol` · `4 1-c 2-a` · `?` to skip | Grades all 10. Shows your score, then explains just the ones you missed and links the textbook section to reread. |
| **Enter** | Next 10. Questions you missed come back in a different form until you get them right. |
| "just chapter 3", "exam 2 stuff" | Narrows the next sets to those chapters. |
| **W** | Your weak spots by chapter, with reading links, plus a quiz on only those. |
| **K** | Switch class. |
| **X** | Done: shows a session summary. |

**How sets are built**

- About 4 questions from your weak spots: past misses, low confidence, and chapters flagged from your real grades.
- About 3 from your next exam's coverage, or about 5 when the exam is within a week.
- About 3 from the rest of the term so far.
- Formats match real exams: multiple choice, select-all, matching, ordering, numeric with units and sig figs, multi-step, fill-in, true/false-with-fix, short answer, scenarios. Every set includes at least two unusual formats or edge cases, so nothing on the real exam is new to you.

Self-study courses (built with `/custom-curriculum`) appear in their own section and work the same way.

**Where your data lives:** a single Google Sheet in your Drive named `llmMemory__studyPrompt__calendarSynced__studyMemory`. Nothing personal is stored in this repo.

---

## Class scanning (Claude Code)

`claude-project/` is a self-contained Claude Code project.

1. Clone this repo and open a Claude Code session **inside `claude-project/`**.
2. Say anything (e.g. "set up"). Claude reads `CLAUDE.md`, installs what it needs (`uv`, Python, dependencies), and creates your local config, asking only for what it can't figure out. Then it lists the available skills.
3. Your personal details (name, school D2L address, SSO host, email, calendar IDs) go only in `config/personal.local.md`, which is never uploaded.

Main skills:

- `/academic-import` scans a class into Google Calendar for the first time. Its weekly overviews list every reading with direct chapter links.
- `/academic-sync` re-scans a class and builds upcoming weeks.
- `/daily-overview` runs at 5am each day and emails one update per class: new announcements, new grades with feedback, missed deadlines, and what's due today.
- `/academic-prefs`
- `/custom-curriculum` builds a self-study course from real open course material online.
- `/audio-lectures`
- `/shift-sync`
