---
name: tt-human
description: >-
  Humanize a TikTok caption, script, on-screen text or comment reply: strip em
  dashes, AI slop words, TikTok bait ("follow for part 2", "wait for it") and
  invisible characters with humanize.py, then score it with detect.py. Use
  when the user asks to humanize or de-slop TikTok copy, asks if a TikTok
  draft sounds like AI, or when another tt-* skill hands over a draft.
license: MIT
metadata:
  maintainer: Ian Ryan Kirk
---

# tt-human

Two tools, both run. Adapted from the humanizer in Jake Schincariol's
instagram-agent-skill.

```bash
python "${CLAUDE_SKILL_DIR}/humanize.py" draft.txt --report        # clean it, show what changed
python "${CLAUDE_SKILL_DIR}/humanize.py" draft.txt -o clean.txt    # write the clean version
python "${CLAUDE_SKILL_DIR}/detect.py" draft.txt                    # score it, five checks
python "${CLAUDE_SKILL_DIR}/detect.py" draft.txt clean.txt          # before and after
```

`${CLAUDE_SKILL_DIR}` is this skill's folder. On macOS or Linux, use `python3`
if `python` is not found.

Both read `slop.json`: 165 stock words and phrases with plain replacements, 18
invisible character classes, 11 typographic substitutions and 19 structural
tells. The last block of phrases and structures is TikTok-specific. Edit it:
if the user always says a word the lexicon strips, take it out.

## Why it matters on TikTok

Scripts are said out loud and captions are short. A line nobody would say
sounds wrong in the first take, and one stock phrase in a two-line caption is
half the caption.

## Fixed automatically

1. **Invisible characters**: zero-width spaces and joiners, word joiners, soft
   hyphens, BOMs, tag characters, non-breaking and narrow spaces.
2. **Typography**: em dash to comma, en dash to hyphen, curly quotes to
   straight, ellipsis to three dots.
3. **The lexicon**: delve, leverage, robust, seamless, plus the TikTok block:
   "follow for part 2", "wait for it", "watch till the end", "this hack will
   change your life", "the algorithm loves", "in today's TikTok".

## Flagged, not fixed

Changing a sentence's shape needs judgement, so these come back for a rewrite:
"It's not just X, it's Y", rule-of-three triads, staged one-word questions,
the video preamble, emoji bullet lists, shouted words, hashtag walls, filler
tags (#fyp, #foryou, #viral), part 2 bait, "wait for it", reflex follow bait,
and uniform sentence length.

## The five checks

| check | measures |
| --- | --- |
| BURSTINESS | sentence length variation |
| SPECIFICITY | numbers and names per 100 words |
| SLOP DENSITY | lexicon hits per 100 words |
| FINGERPRINT | invisible characters, em dashes, curly quotes |
| VOICE | contractions, personal pronouns, structural tells |

PASS needs 70 overall with no check under 55. Texts under about 25 words are
"too short to judge" on three checks, which is common for captions; read the
slop and fingerprint checks for those.

## Say this honestly

These are local heuristics. They are not GPTZero, Originality, Copyleaks or
any other detector, they call no service, and they cannot promise any
detector's verdict. Never tell the user a text is undetectable.

## Order

1. `humanize.py draft.txt -o clean.txt --report`
2. Rewrite the flagged lines by hand.
3. `detect.py draft.txt clean.txt` for the before and after.
4. Show the cleaned text and the score together. Never the score alone.
