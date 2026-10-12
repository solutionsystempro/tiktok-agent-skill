---
name: tt-hook
description: >-
  Write and score the first one to three seconds of a TikTok as three layers,
  the spoken line, the on-screen text and the first visual, using 20 hook
  formulas in hooks.json and hookscore.py. Use when the user wants a TikTok
  hook, asks why their TikToks get swiped in the first seconds, or wants TikTok
  hook options scored. Not for YouTube or Instagram hooks.
license: MIT
metadata:
  maintainer: Ian Ryan Kirk
---

# tt-hook

A TikTok hook is three things that land at once: what the viewer hears, what
they read, and what they see. Most hooks get written as one sentence and the
other two layers are left to chance. This skill writes all three and scores
them.

```bash
python "${CLAUDE_SKILL_DIR}/hookscore.py" hooks.txt
python "${CLAUDE_SKILL_DIR}/hookscore.py" --spoken "..." --text "..." --visual "..."
python "${CLAUDE_SKILL_DIR}/hookscore.py" hooks.txt --json
```

`${CLAUDE_SKILL_DIR}` is this skill's folder, so the command works from any
directory. On macOS or Linux, use `python3` if `python` is not found.

## Before you write

1. Read `~/.claude/tiktok/voice.md` if it exists. If not, ask for three of the
   user's own TikToks (transcripts or captions are enough) and offer to write
   the file from them. Hooks are said out loud, so the voice matters.
2. Read `${CLAUDE_SKILL_DIR}/hooks.json`: 20 formulas, each with a spoken
   template, an on-screen line, a first visual, what it is for and how it goes
   wrong. These are starting shapes written for this pack, not measured
   winners.
3. If `~/.claude/tiktok/swipe.md` exists (written by `/tt-viral`), read it. The
   user's own collected evidence beats the defaults.
4. If the idea has no specific true thing in it (a number, an object, a result,
   a person), ask one batched question before writing.

## The loop

1. **Pick three formulas** that fit the idea. Different formulas, not three
   rewrites of one.
2. **Write three layers for each**, in the file format the tool reads:

   ```
   spoken: This chair cost $1,400. Here is what that buys you.
   text: $1,400 CHAIR. WORTH IT?
   visual: Hand slaps the price sticker onto the chair.
   ```

   Blank line between hooks. `text:` is the on-screen line, `visual:` is one
   sentence describing frame one.
3. **Score them** with `hookscore.py` and show the ranking. Each hook gets a
   score per layer and a combined score. A missing layer costs 10 points and
   blocks STRONG.
4. **Fix the weakest layer** of the top hook and re-run. If the top hook is
   under 50, the idea needs a different angle, not more editing.
5. Run the spoken and on-screen lines through `/tt-human` before showing them.
6. Hand the winner to `/tt-script`.

## What each layer is scored on

| layer | checks | what fails |
| --- | --- | --- |
| SPOKEN | length (4 to 8 words is about 3 seconds at 165 wpm), something concrete, something at stake, payload near the front, aimed at the viewer | greetings, "in this video", "stop scrolling", "wait for it" |
| ON-SCREEN | readable at a glance (about six words), concrete, adds to the spoken line instead of repeating it | a paragraph on screen, hashtags, emoji-only cards |
| VISUAL | something moving or already shown, a concrete subject, no static opener | logo, title card, still face waiting to talk, slow establishing shot |

The visual check reads your sentence about the frame, not the frame. Write
what the viewer actually sees.

## Say this honestly

These are local heuristics. None of the weights were fitted to TikTok
performance data, and the tool cannot predict views. It is good at catching
weak openings before filming. After posting, the retention numbers in TikTok
Studio are the real judge, and `/tt-retention` reads them.

## Rules

- **Never fabricate.** No invented numbers, results or credentials. If a hook
  needs a number the user has not given, write `{{your number}}` and flag it.
- **The on-screen line is not a subtitle of the spoken line.** Shorter, and
  ideally the other half of the idea.
- **The first frame is part of the hook.** If the user films a still intro,
  say so.
- **Nothing is posted.** This skill writes. The user films and posts.
