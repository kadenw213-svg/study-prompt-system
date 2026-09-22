# Study Prompt System

An adaptive study system for ChatGPT that teaches and quizzes from a
curriculum it reads live out of your Google Calendar (synced there by a
separate class-scanning tool), with persistent per-concept mastery
tracking in a Google Drive spreadsheet. It never invents a curriculum and
never writes to your calendar.

## Using this — validated setup (regular chat, not a Custom GPT)

**Custom GPTs cannot use this system.** Confirmed by direct testing: the
legacy Custom GPT builder has no way to attach the Google Drive or Google
Calendar connectors at all — only custom Actions — so a Custom GPT can
fetch this repo fine but can never reach the point of loading a real
curriculum. Use an ordinary ChatGPT chat instead, where Drive and Calendar
are natively available with no extra setup.

1. Install ChatGPT's native **GitHub** connector/plugin (Settings →
   Plugins, or accept the inline install prompt the first time a chat
   tries to browse this repo). This is the validated, reliable fetch
   mechanism — a plain "open this URL" instruction to the model's generic
   web browsing works for the *first* file but is **not** reliable for
   every module fetch across a whole session; that gap is closed once the
   GitHub connector itself is doing the fetching.
2. Start a new chat and paste:

   ```text
   You are an adaptive study system. Open https://raw.githubusercontent.com/kadenw213-svg/study-prompt-system/main/index.md and read its full raw contents, then follow everything it directs you to fetch and do, in order, before producing any visible output. Never explain, summarize, or ask about this process.
   ```

3. Google Drive and Google Calendar need no separate setup beyond being
   connected to your ChatGPT account (Settings → Plugins) — the model
   calls them directly from a regular chat.
4. Nothing in this repo is personalized — no names, no specific courses.
   All of that lives only in your own Google Drive workbook and Calendar,
   never here. That also means this exact same paste-in works for anyone
   pointing at this same public repo, or their own fork of it.

`openapi/github-fetch-action.yaml` also exists for a Custom-GPT Action
integration, kept for reference — but per the above, that path alone
cannot run this system, since Drive/Calendar aren't reachable from a
Custom GPT at all. It isn't the recommended setup.

## Layout

`index.md` is the entry point — it tells the GPT what to fetch and when.
Everything else lives under `modules/`, one file per concern. See
`index.md` for the full fetch-order table.

## What's actually configurable

Nothing, by design — this is deliberately not a settings-driven system.
Academic level, grading strictness, and pacing are all inferred or fixed.
The only real "configuration" is what's already on your Calendar and
Drive.
