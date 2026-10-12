---
name: tt-plan
description: >-
  Plan a week of TikToks: what to film, which hook formula, which search
  phrase or trend each one targets, and a posting rhythm the user can keep,
  built from the user's swipe file, keyword map, trend analysis and Studio
  numbers. Use when the user asks for a TikTok content plan or a TikTok
  posting schedule for the week.
license: MIT
metadata:
  maintainer: Ian Ryan Kirk
---

# tt-plan

One page that says what to film this week and why.

## Inputs, in order of value

1. The user's own TikTok Studio numbers, via `/tt-retention`: which recent
   videos held viewers and which lost them in the first seconds.
2. `~/.claude/tiktok/swipe.md` from `/tt-viral`: formulas over-indexing in the
   niche.
3. The keyword map from `/tt-seo`: phrases people search.
4. The "make this week" list from `/tt-trends`.
5. `~/.claude/tiktok/voice.md`: positions, proof, what is off limits.

Use what exists. If none of it does, say the plan is built on defaults and
suggest running `/tt-retention` and `/tt-seo` first.

## The plan

Ask how many videos the user can actually make this week. Plan that number,
not more. A rhythm they keep beats a target they miss; do not quote a "best
posting frequency" or "best time to post" as fact, because there is no
verified figure for either. If they want timing, point them to the follower
activity data in their own TikTok Studio, where available.

For each video:

```
TUE  #1  "How do you get wax out of carpet?"
     job:      search (primary keyword from /tt-seo)
     formula:  #5 The Typed Question
     hook:     spoken / on screen / first visual, scored by /tt-hook
     length:   ~20s
     why:      question appeared in 3 of your pasted lists
```

Mix the jobs across the week:

- **search**: answers a phrase from the keyword map
- **proof**: shows a result the user can stand behind
- **trend**: uses an emerging or rising trend from `/tt-trends`, only if it
  fits the niche
- **conversation**: a video reply to a real comment, from `/tt-comment`
- **series**: the next part of something that already worked

## Close

End with a short list: what to film first, and what to measure next week (the
hook leak and completion numbers in Studio, read with `/tt-retention`).

Nothing is scheduled or posted by this skill. TikTok's Content Posting API can
post for a user only through an app the user authorizes; TikTok's guidelines
require the user's express consent before content is uploaded, and content
from unaudited apps is restricted to private viewing:
https://developers.tiktok.com/doc/content-sharing-guidelines/ . This pack is
not such an app. The user posts.
