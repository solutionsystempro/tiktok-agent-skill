---
name: tt-viral
description: >-
  Rank TikToks the user collected by hand with swipe.py: views over that
  account's median (or followers, labelled per row), the hook formula named
  from tt-hook's hooks.json, and a swipe file. Use when the user asks which
  TikToks in their niche are outperforming, wants to reverse engineer a TikTok
  account, or wants a TikTok swipe file. Reads what the user pastes, never
  scrapes.
license: MIT
metadata:
  maintainer: Ian Ryan Kirk
---

# tt-viral

```bash
python "${CLAUDE_SKILL_DIR}/swipe.py" captured.tsv
python "${CLAUDE_SKILL_DIR}/swipe.py" captured.csv --out ~/.claude/tiktok/swipe.md
```

`${CLAUDE_SKILL_DIR}` is this skill's folder. On macOS or Linux, use `python3`
if `python` is not found. The tool reads `../tt-hook/hooks.json` and
`../tt-hook/hookscore.py`, so install `tt-hook` next to it. Without them it
still ranks, but cannot name formulas or score hooks.

## The idea

Raw views are not evidence. A big account at 400K views had an ordinary day. A
small account at 400K found something. So the ranking is the **multiple over
the account's own baseline**:

- **median** of that account's recent video views, when the user has it (the
  better baseline), shown as `med`
- **follower count** otherwise, shown as `fol`

Every row is labelled with the baseline it used. If a batch mixes the two, the
header says "mixed" with the count of each, because a multiple over followers
and a multiple over a median are not on the same scale. Compare like with
like.

## Collecting, by hand

Ask the user for 6 to 12 accounts: some in the same niche, some with the same
audience in a different niche, a couple much bigger for format only. For each,
the user watches on their own phone and writes down, per video:

| column | notes |
| --- | --- |
| account | handle |
| followers | from the profile, as shown (48K is fine) |
| median | middle view count of the last 12 or so videos on the grid |
| views | this video, as shown (1.2M is fine) |
| hook | the first spoken line, or the first on-screen text, word for word |

Tab- or comma-separated with a header row. `412K`, `1.2M`, `1,2M` and
`412,000` all parse. A cell that is not a count is reported and the row is
skipped or the field ignored, never guessed. A header-only template is in
`${CLAUDE_SKILL_DIR}/swipe.tsv`.

### Breakdown columns

Five optional columns turn the ranking into a breakdown. The user fills them
in while watching, or you fill them from a transcript the user pastes. Never
guess them from a thumbnail or a title.

| column | what goes in it |
| --- | --- |
| hook_type | the kind of opening, ideally a `tt-hook/hooks.json` name. Blank: the classified formula is used |
| topic | a short topic label, reused consistently across rows |
| length_s | seconds: `34`, `34s` or `0:34` |
| structure | list, story, myth-bust, tutorial, reaction, comparison, ... |
| cta | the ask at the end: follow, comment keyword, part 2, save, none |

The report then aggregates across the batch: the most common hook types,
topics, structures and CTAs, the median length, and which values the **top
quartile by outperformance** shares more than the batch overall (a value has
to appear in at least two top-quartile posts to count). For the 30-day
workflow in `/tt-plan`, this runs on 50 posts: five creators, ten best posts
each.

**Rules that are not negotiable:**

- **No scraping, no unofficial APIs, no browser automation, no third-party
  scraping services.** TikTok's US Terms of Service (version of July 15, 2026), section 3.4, prohibit
  automated scraping or extraction of platform data except as approved in
  writing by TikTok: https://www.tiktok.com/legal/page/us/terms-of-service/en
- The official **Research API** is limited to approved academic and
  not-for-profit researchers independent of commercial interests, so it is not
  a route for this: https://developers.tiktok.com/products/research-api/
- The **Display API** only returns the authorizing user's own videos, so it
  covers the user's account, not competitors:
  https://developers.tiktok.com/doc/display-api-get-started/
- **Copy the formula, never the video.** The hook shape, the length, the
  structure. Not their script, voice or footage. Attribute every row.
- Nothing is followed, liked, saved or commented on the user's behalf.

## Reporting

1. Which formulas over-index in the top third, with counts. Small counts are
   not findings; say so.
2. What the top third share that the bottom third do not: hook length, spoken
   hook score, whether the first frame shows the result.
3. The unclassified rows. Read them by hand. A repeated unnamed shape is a
   formula worth adding to `tt-hook/hooks.json`.
4. The sample size, in plain words. Forty videos across six accounts supports
   a tentative claim. Ten does not.

Then write the user's version of the top two or three formulas, in their own
story, and hand each to `/tt-hook`.

Write the swipe file to `~/.claude/tiktok/swipe.md`. `/tt-hook` and `/tt-plan`
read it.
