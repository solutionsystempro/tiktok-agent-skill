---
name: tt-repurpose
description: >-
  Turn a YouTube Short, Instagram Reel or long video transcript into a
  TikTok-native version (reworked three-layer hook, new length, on-screen
  text, caption), and write a per-video cross-post pack checked by
  crosspost.py. Use when the user wants to adapt existing video content for
  TikTok, cut a long transcript into TikToks, or cross-post a TikTok.
license: MIT
metadata:
  maintainer: Ian Ryan Kirk
---

# tt-repurpose

A Reel or a Short reposted to TikTok as-is often carries the wrong opening,
the wrong length and another platform's habits. This skill rebuilds it for
TikTok from the transcript, using the rest of the pack.

## Input

- **A short (Reel or YouTube Short):** the transcript, the on-screen text, a
  one-line description of the first frame, and its length.
- **A long video:** the transcript with timestamps if possible, and the topic.

Work only from what the user provides and content the user owns or has the
rights to. Do not download videos from any platform on the user's behalf.

## Short to TikTok

1. **Find the one idea.** If the source has two, it becomes two TikToks.
2. **Rebuild the hook as three layers** with `/tt-hook`: spoken, on-screen,
   first visual. Instagram and YouTube hooks often open on a line that works
   with that platform's interface; re-score it, do not assume it transfers.
3. **Recut the length** with `/tt-script` and `beats.py --target`. Cut the
   setup before the hook, the "follow for more" ending, and any line that
   refers to another platform ("link in my YouTube description", "check my
   Reels").
4. **Rewrite the on-screen text** to six words or fewer per card.
5. **New caption** with `/tt-caption`. Search phrase from `/tt-seo` if there is
   one.
6. **Clean export.** Tell the user to export the original edit without another
   platform's watermark. Whether TikTok treats watermarked reposts differently
   is unverified, but a visible competitor logo does not help the viewer.

## Long video to TikToks

1. Read the transcript and list every self-contained moment: a claim with its
   proof, a story with its turn, a mistake with its fix, a number with its
   meaning. Each needs to make sense with no context.
2. Rank them by how specific they are. A moment with a number, a name or a
   visible result beats an opinion.
3. For the top three to five: the timestamp range, a three-layer hook, the cut
   script (`beats.py`), on-screen text and a caption.
4. Flag any moment that only works with the long video's context. It is not a
   TikTok yet.

## Cross-post pack, per video

Repurposing runs both ways. For every finished video, write one pack file
with a TikTok caption, a YouTube Shorts title and description, and an
Instagram Reels caption, each written for its own platform, then check it
with the tool in `tt-caption`:

```bash
python "${CLAUDE_SKILL_DIR}/../tt-caption/crosspost.py" pack.txt
```

The format and the limits it checks (verified for TikTok and YouTube,
unverified for Instagram) are in `/tt-caption`. Remove mentions of the other
platforms from each version, and export each upload without another
platform's watermark.

## Output

```
REPURPOSE  source: Reel "3 screws shelf" (34s)

TIKTOK VERSION
  hook:      spoken "This shelf holds 40 kilos on three screws."
             on screen "3 SCREWS. 40 KILOS."  visual: shelf already loaded, hand pressing down
             score 84 STRONG
  length:    22.6s (was 34s), cut the 6s intro and the "follow for part 2" ending
  cards:     4
  caption:   ready, linter READY
  crosspost: TikTok / Shorts title + description / Reels, crosspost.py READY
  removed:   "link in bio on Instagram", 2 hashtags from the original
```

## Rules

- Never invent results, numbers or quotes the source does not contain.
- Keep the user's voice; read `~/.claude/tiktok/voice.md`.
- Run every line through `/tt-human`.
- Nothing is posted. The user uploads it.
