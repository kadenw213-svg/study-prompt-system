# Study Prompt System

An adaptive study system for a ChatGPT Custom GPT that teaches and quizzes
from a curriculum it reads live out of your Google Calendar (synced there
by a separate class-scanning tool), with persistent per-concept mastery
tracking in a Google Drive spreadsheet. It never invents a curriculum and
never writes to your calendar.

## Using this with your own Custom GPT

This repo is the GPT's instruction set, hosted here instead of uploaded as
a static file, specifically so it never goes stale: your GPT fetches the
current version of these files live, every session, via a small GitHub
Action instead of a one-time upload.

To point your own Custom GPT at this repo:

1. In the GPT builder, add an Action using the schema in
   `openapi/github-fetch-action.yaml` (no authentication needed — this repo
   is public; the schema already points at
   github.com/kadenw213-svg/study-prompt-system).
2. Set the GPT's Instructions field to a short bootstrap pointer telling it
   to fetch `index.md` on its very first turn and follow what it says. See
   `openapi/github-fetch-action.yaml`'s comments for the exact wording used
   by the original author.
3. Connect a Google Drive tool and a Google Calendar Action with read
   access — both are required; the GPT will say so plainly if either is
   missing.
4. Nothing in this repo is personalized — no names, no specific courses.
   All of that lives only in your own Google Drive workbook and Calendar,
   never here.

## Layout

`index.md` is the entry point — it tells the GPT what to fetch and when.
Everything else lives under `modules/`, one file per concern. See
`index.md` for the full fetch-order table.

## What's actually configurable

Nothing, by design — this is deliberately not a settings-driven system.
Academic level, grading strictness, and pacing are all inferred or fixed.
The only real "configuration" is what's already on your Calendar and
Drive.
