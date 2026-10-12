---
name: tt-caption
description: >-
  Write and lint a TikTok caption and on-screen text with caption.py: the
  2,200 UTF-16 unit limit, a preview of the first line before the cut,
  hashtag count and placement, search keywords and emoji. Use when the user
  wants a TikTok caption, asks about TikTok hashtags or caption length, or
  wants their TikTok on-screen text checked. Not for Instagram or YouTube.
license: MIT
metadata:
  maintainer: Ian Ryan Kirk
---

# tt-caption

```bash
python "${CLAUDE_SKILL_DIR}/caption.py" caption.txt
python "${CLAUDE_SKILL_DIR}/caption.py" caption.txt --keywords "sourdough starter,bread recipe"
python "${CLAUDE_SKILL_DIR}/caption.py" caption.txt --onscreen cards.txt --keywords "sourdough starter"
```

`${CLAUDE_SKILL_DIR}` is this skill's folder. On macOS or Linux, use `python3`
if `python` is not found.

## What the linter knows, and how sure it is

| check | basis |
| --- | --- |
| **Length: 2,200 UTF-16 code units** | Verified. The Content Posting API documents the caption (`title`) field as "The maximum length is 2200 in UTF-16 runes": https://developers.tiktok.com/doc/content-posting-api-reference-direct-post/ . Most emoji are two units, so the tool counts units, not characters. The in-app limit may be different; that is unverified, and this tool uses the documented API number. |
| **First-line preview** | Approximation, unverified. The tool shows the first line up to 90 characters (`--truncate` to change). The real cut depends on device, font and what else is on screen. |
| **Hashtag count** | **Heuristic, not a TikTok rule.** The tool warns above 5 because a wall of tags pushes the searchable words out of view. We could not verify a published TikTok hashtag cap. |
| **Hashtag placement** | Heuristic: words first, tags after. |
| **Search terms** | Checks your phrases are in the caption, in the visible line and in the on-screen text. How TikTok weights each place in search is not published; treat this as "put the phrase where a person would read it". |
| **Emoji** | Counted as graphemes, so a skin tone or a family emoji is one. Warns above 4 per 100 characters and on a caption that opens with one. |
| **Links** | Warns: caption links are generally not clickable (unverified for every account type). |

## The shape

```
Line 1     the line that shows before the cut. Restate the hook's promise or
           the search phrase, plainly. Never a hashtag, never a greeting.
Body       optional. A few short lines: the context, the steps, the search
           phrases in normal sentences.
The ask    one. Comment a word, save it, follow the series. One.
Hashtags   a few specific ones on the last line, or none.
```

## On-screen text

Pass the cards with `--onscreen`, one per line. Each card is checked for
length (eight words or fewer, heuristic) and stray hashtags, and the search
phrases are checked against the cards too. Keep text out of the bottom and
right edge of the frame, where the caption and buttons sit.

## The loop

1. Get the search phrases from `/tt-seo` if the user has run it, or ask for
   two or three.
2. Draft the caption and the cards.
3. Run `/tt-human` on both.
4. Run `caption.py`. Fix every FAIL. Decide every WARN out loud.
5. Print the copy-ready caption, the cards, and the receipt:

```
CAPTION READY
length:     312 / 2200 UTF-16 units
first line: 64 characters, likely shows whole
ask:        one, comment STARTER
hashtags:   3 (heuristic guide: up to 5)
search:     "sourdough starter" in line 1 and on card 1
linter:     READY
```

Nothing is posted. The user pastes it into TikTok.
