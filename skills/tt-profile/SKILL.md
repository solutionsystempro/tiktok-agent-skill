---
name: tt-profile
description: >-
  Score a TikTok profile out of 100 against a 10-part rubric (name, bio, link,
  pinned videos, niche consistency, posting cadence, grid, series, photo) and
  rewrite what loses points. Use when the user wants a TikTok profile audit,
  a TikTok bio rewrite, or asks why TikTok profile visitors do not follow.
license: MIT
metadata:
  maintainer: Ian Ryan Kirk
---

# tt-profile

Most profile visits come from one video. The profile then has a few seconds to
answer: is there more of that here, and is it for me.

## Input

Ask the user to paste or screenshot: display name, username, bio, link (if
any), what is pinned, the covers and dates of the last nine videos, and any
playlists or series names. Do not log into TikTok on their behalf and do not
open their profile with a browser tool.

## Score it

Read `${CLAUDE_SKILL_DIR}/rubric.json`: ten items, 100 points, each with what
full marks looks like and how it usually fails. Score every item, show the
table, give the total. Be strict; a generous score is useless.

```
PROFILE SCORE  46/100

  name               4/10   name only, nothing searchable
  bio promise        6/14   says what, not who for
  pinned             0/14   nothing pinned
  niche consistency  8/14   two topics in the last nine
  cadence            7/10   steady, twice a week
  ...
```

## Platform details, and how sure we are

These vary by account type, region and app version and were **not verified**
for this pack. Check them in the user's app before advising:

- the bio character limit
- whether the account can show a clickable link in the bio (has been tied to
  account type and follower thresholds)
- how many videos can be pinned
- whether playlists are available on the account

Do not state a number for any of these as fact.

## Then rewrite, in order of points lost

1. **Name**: three options in the form `{Name} | {topic in searched words}`.
2. **Bio**: who it is for and what they get, then one proof or one ask. Three
   options that fit the user's field limit.
3. **Pinned**: which existing videos to pin and why, one job each (proof,
   explanation, introduction). If the right video does not exist, say what to
   make, and hand it to `/tt-hook`.
4. **Niche**: if the last nine videos span several topics, name the one the
   numbers favour (ask for views, or use `/tt-retention`) and say so plainly.
5. **Cadence**: a rhythm the user can keep, not a number from a guru.
6. **Grid and series**: cover text of a few words, and a name for each
   recurring format.

Run every rewrite through `/tt-human`. Re-score at the end and report the
honest delta.

Nothing is changed on TikTok by this skill. The user edits each field.
