---
name: tt-script
description: >-
  Write a short-form TikTok script with a timed beat sheet from beats.py:
  hook beat, body beats, payoff and loop, on-screen text and B-roll
  directions, checked against a target length. Use when the user wants a
  TikTok script, a TikTok beat sheet, or asks how long their TikTok script
  runs. Not for long-form YouTube scripts.
license: MIT
metadata:
  maintainer: Ian Ryan Kirk
---

# tt-script

Turns one idea and a scored hook into a script someone can film today.

```bash
python "${CLAUDE_SKILL_DIR}/beats.py" script.txt --target 30
python "${CLAUDE_SKILL_DIR}/beats.py" script.txt --wpm 180 --target 45
python "${CLAUDE_SKILL_DIR}/beats.py" script.txt --json
```

`${CLAUDE_SKILL_DIR}` is this skill's folder. On macOS or Linux, use `python3`
if `python` is not found.

## Before you write

1. Read `~/.claude/tiktok/voice.md`. Use the speaking pace in it as `--wpm` if
   the user has timed themselves.
2. Get the hook from `/tt-hook`, all three layers. If there is none, run that
   first.
3. Ask for the target length. If the user has no view, suggest the shortest
   length that delivers the idea. TikTok's maximum lengths for in-app recording
   and uploads have changed several times and are **unverified** here, so do
   not quote a limit; check the app.

## Script format

One spoken beat per line. Directions go on their own line in square brackets
and take no time on the clock:

```
[TEXT: 3 SCREWS ONLY]
This shelf holds 40 kilos with three screws.
Most people use eight. You need three, in the right spot.
[B-roll: drilling into the stud]
First screw goes into the stud, not the drywall.
That is the whole trick. Three screws, forty kilos.
```

## The shape

```
0:00 - 0:03   HOOK     spoken + on-screen + first visual, from /tt-hook
next beat     STAKE    why this matters to the person watching, one line
body          BEATS    one idea per beat, the picture changes every beat
end           PAYOFF   deliver what the hook promised, then one ask
last line     LOOP     echo a word from the hook so the replay joins cleanly
```

## The loop

1. Write the script in the user's voice: contractions, short lines, nothing
   they would have to rehearse.
2. Run `beats.py` with the target. Fix every flag: a hook beat over 3 seconds,
   any beat over 4 seconds, three beats in a row with nothing concrete, no
   loop, length off target by more than 10%.
3. Run it through `/tt-human`.
4. Print the script, the on-screen text as a separate timed list, and a short
   receipt:

```
SCRIPT READY
hook:       #16 Time Box, 82 STRONG (spoken 85 / on-screen 100 / visual 70)
length:     24.1s over 8 beats at 165 wpm, target 25s
on-screen:  5 cards
caption:    run /tt-caption next
```

Timings are estimates from word count. They are close enough to plan an edit,
not a replacement for a test recording.

## Rules

- **One idea per video.** Two ideas is two videos. Say so.
- **Numbers over adjectives.** If the number is missing, ask, or leave
  `{{your number}}` and flag it. Never invent one.
- **Burned-in captions** for the spoken body: many people watch muted. Keep
  them out of the bottom of the frame where the caption and buttons sit.
- **Sounds.** If the script relies on a trending sound, remind the user that
  business accounts may have a more limited music library (unverified for
  every region, check in the app).
- **Nothing is posted.** This skill writes. The user films and posts.
