---
name: tt-plan
description: >-
  Plan and batch a month of TikToks (the "tt-month" workflow): the top 5
  creators in the niche, their 10 best posts each as a 50-row swipe file,
  breakdown, question research, 30 scripts, a filming-day sheet grouped by
  set, outfit and location, a 30-day posting calendar and a daily manual
  engagement checklist. Use when the user wants a 30-day TikTok batch, a
  TikTok content month, a TikTok content calendar or a weekly TikTok plan.
license: MIT
metadata:
  maintainer: Ian Ryan Kirk
---

# tt-plan

The backbone of the pack. One month of TikToks, researched from what is
already working in the niche, written in one sitting and filmed in one
session of one to two hours.

Every step uses another skill. This one keeps the order and writes the
files. The template for the month folder is `templates/month.md` in this
pack; copy it as the folder's `README.md`.

## Where the month lives

`~/.claude/tiktok/month-YYYY-MM/`, for example `~/.claude/tiktok/month-2026-11/`:

```
README.md          from templates/month.md: the month at a glance, progress boxes
creators.md        step 1
swipe.tsv          step 2, the 50-row swipe file
swipe.md           step 3, written by swipe.py
questions.md       step 4, written from questions.py and kwmap.py output
scripts/01.md ... scripts/30.md   step 5
filming-day.md     step 6
calendar.md        step 7
engagement.md      step 8
```

## Step 1. Five creators

Ask the user for the **top 5 creators in their niche**: accounts their
audience also watches, slightly ahead of them, posting the kind of video the
user can make. If they cannot name five, they can search the niche's main
phrase on TikTok and pick from the results by hand. Write `creators.md` with
each handle and one line on why it is on the list. Do not name creators
yourself from memory; the user's niche today is what counts.

## Step 2. Fifty posts, by hand

For each creator, the user collects that creator's **10 best-performing
posts**, which gives a 50-row swipe file. Start from the header in
`../tt-viral/swipe.tsv` and save it as `swipe.tsv` in the month folder.

The user fills in, per post: account, followers, median (middle view count
of their recent videos), views and the hook, by watching on their own phone.
Building the file by hand works. If the user chooses to use an export from a
tool they picked, that choice and its compliance are the user's; this pack
does not name, recommend or run any collector, and never scrapes TikTok
(TikTok US Terms of Service, version of July 15, 2026, section 3.4:
https://www.tiktok.com/legal/page/us/terms-of-service/en).

The breakdown columns (`hook_type`, `topic`, `length_s`, `structure`,
`cta`) can be filled by the user, or by you from a transcript the user
pastes. Never guess them from a title.

## Step 3. Break it down

Run `/tt-viral`:

```bash
python "${CLAUDE_SKILL_DIR}/../tt-viral/swipe.py" swipe.tsv --out swipe.md
```

Report, in plain words: the most common hook types, topics, structures and
CTAs; the median length; and what the top quartile by outperformance has in
common that the batch does not. Fifty posts from five accounts is a sample,
not proof. Say so.

## Step 4. Question research

Run `/tt-seo`: the user pastes questions from TikTok search suggestions,
"People also ask" boxes in web search, Q&A sites and forum threads, and the
comments under their own videos. Cluster them:

```bash
python "${CLAUDE_SKILL_DIR}/../tt-seo/questions.py" questions.txt --seed "{niche word}"
```

Write `questions.md`: the clusters, and the script ideas each one maps to.

## Step 5. Thirty scripts

Pick 30 ideas: mostly the question clusters (search) and the structures and
hook types that stood out in step 3 (proof that the shape works in this
niche), told with the user's own stories and numbers from `voice.md`. Then for
each:

1. three-layer hook with `/tt-hook` (spoken, on-screen, first visual), scored
2. script and beat sheet with `/tt-script`
3. caption, and the cross-post pack if the user posts elsewhere, with
   `/tt-caption`
4. `/tt-human` on all of it

Write each to `scripts/NN.md` with a small header the filming sheet needs:

```
# 07  Why is my bread dense?
set: kitchen counter   outfit: apron   location: home kitchen
length: ~24s   formula: #20 Mistake Count   hook score: 81
props: dense loaf, good loaf, knife
```

Never invent a result, number or story. Use `{{your number}}` and flag it.

## Step 6. Filming-day sheet

Group the 30 scripts by **set, then outfit, then location** so the whole
month can be filmed in one 1 to 2 hour session with the fewest changes.
For each group, `filming-day.md` lists:

- the set, outfit and location, and the props to have ready
- each script in the group: number, title, the shot list (frame one first,
  then each beat's shot), and the on-screen text with timings
- a rough time budget per group, and a running total against two hours

If the total is over two hours, say which scripts to move to a second session
rather than squeezing the takes. Outfit changes between groups let videos
posted on different days look like different days.

## Step 7. Thirty-day calendar

`calendar.md`: one row per day, date, script number, title, the job
(search / proof / trend / conversation / series), and the caption file. Mix
jobs across each week. Do not quote a "best time to post" or "best
frequency" as fact; there is no verified figure. If the user wants timing,
point to the follower activity in their own TikTok Studio, where shown.

Leave two or three open slots for a trend from `/tt-trends` or a video reply
from `/tt-comment` that comes up during the month.

## Step 8. Daily engagement checklist

`engagement.md`, a checklist the **user** works through by hand each day.
Nothing in it is automated and nothing is done on the user's behalf:

```
[ ] post today's video (calendar.md)
[ ] reply to new comments on today's and yesterday's videos (drafts: /tt-comment)
[ ] pick one comment worth a video reply, add it to an open slot
[ ] leave a few thoughtful comments on other creators' videos in the niche
[ ] note anything that did unusually well or badly for the end-of-month review
```

## End of month

Run `/tt-retention` on the month's Studio export and compare against the
step 3 breakdown. Carry what held viewers into next month's folder.

## Never

Nothing is posted, scheduled, liked, followed or commented by this skill.
TikTok's Content Posting API can post only through an app the user
authorizes, with the user's express consent before upload, and unaudited apps
are limited to private viewing:
https://developers.tiktok.com/doc/content-sharing-guidelines/ . This pack is
not such an app. The user films and posts.
