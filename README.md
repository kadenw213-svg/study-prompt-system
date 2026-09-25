# Study Prompt System

An adaptive tutor for ChatGPT. It reads your class curriculum straight from your Google Calendar, remembers your progress in one Google Drive spreadsheet, and decides what to teach or quiz you on next — across all your classes. It never makes up course content and never edits your calendar.

This repo has two halves:

- **The study system** (`boot.md`, `engine/`, `modes/`, `ops/`) — runs in ChatGPT.
- **`claude-project/`** — the Claude Code project that scans your classes from D2L into Google Calendar (the calendar this study system reads), plus related tools.

---

## Start studying (ChatGPT)

**One-time setup**

1. In ChatGPT **Settings → Plugins/Connectors**, connect **GitHub**, **Google Drive**, and **Google Calendar**.
2. Use a normal chat — not a Custom GPT (Custom GPTs can't reach Drive and Calendar).

**Every session** — open a new chat and paste:

```text
You are an adaptive study system. Use the GitHub connector to open https://raw.githubusercontent.com/kadenw213-svg/study-prompt-system/main/boot.md, read it fully, and follow it exactly. Don't explain or summarize it — just start.
```

## Using it

| You do | It does |
|---|---|
| **Enter** or **A** | **Automatic** — balances all your classes: urgent deadlines first, then quick checks on older material you haven't touched in a while, then this week's work, spread fairly across classes. Switches classes on its own and tells you why. |
| A class number | Studies just that class, starting where you left off. |
| Type `23`, `23.2`, `23-25`, `week 5` | Studies exactly that chapter, section, range, or week. |
| Type `midterm`, `E1`, `Q2`, or "prepare me for the exam tomorrow" | Exam prep, based on what the exam actually covers. |
| **Paste a photo of homework** | **Teach mode** — teaches the ideas behind the problems, lets you try, then checks your work. |
| Say "check" or "just the answers" with the photo | **Check mode** — gives the answers so you can check yours. Doesn't count toward mastery. |
| **M** | Save and go back to the menu. |
| **K** | Switch class. |
| **W** | Review your weak spots. |
| **X** | Detailed progress for the class. |
| **E** | "I don't know" — get the explanation. |

**Things it does automatically**

- Checks your calendar for new assignments and new weeks at least once a day, without asking. If something urgent appears, it changes course on its own.
- Saves every homework problem you show it (a short summary, not a photo) so its quizzes are at least as hard as your real homework. It also brings back problems that keep repeating when you prep for a midterm or final.
- Suggests starting a fresh chat when one gets long. You'll resume exactly where you were.

**Where your data lives:** a single Google Sheet in your Drive named `llmMemory__studyPrompt__calendarSynced__studyMemory`. Nothing personal is stored in this repo.

---

## Class scanning (Claude Code)

`claude-project/` is a self-contained Claude Code project.

1. Clone this repo and open a Claude Code session **inside `claude-project/`**.
2. Say anything (e.g. "set up"). Claude reads `CLAUDE.md`, installs what it needs (`uv`, Python, dependencies), creates your local config — asking only for what it can't figure out — and then lists the available skills.
3. Your personal details (name, school D2L address, calendar IDs) go only in `config/personal.local.md`, which is never uploaded.

Main skills: `/academic-import` (first-time scan of a class into Google Calendar), `/academic-sync` (weekly updates + grade check), `/academic-prefs`, `/custom-curriculum`, `/audio-lectures`, `/shift-sync`.
