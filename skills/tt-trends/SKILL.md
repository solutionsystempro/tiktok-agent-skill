---
name: tt-trends
description: >-
  Find TikTok trends worth making this week: a guided manual workflow for
  TikTok Creative Center and the For You page, plus trends.py, which analyses
  trend snapshots the user brings (velocity, stage, first seen, niche fit).
  Use when the user asks what is trending on TikTok, which TikTok sounds or
  hashtags to use, or wants to analyse TikTok trend snapshots. The pack
  never scrapes TikTok.
license: MIT
metadata:
  maintainer: Ian Ryan Kirk
---

# tt-trends

Two halves. A manual way to look at trends, and a tool that turns several
looks over time into a decision.

```bash
python "${CLAUDE_SKILL_DIR}/trends.py" week1.csv week2.csv --niche "sourdough,bread"
python "${CLAUDE_SKILL_DIR}/trends.py" snapshots.json --kind sound --top 5 --markdown
python "${CLAUDE_SKILL_DIR}/trends.py" a.csv b.csv --json
```

`${CLAUDE_SKILL_DIR}` is this skill's folder. On macOS or Linux, use `python3`
if `python` is not found.

## Collection: what this pack does and does not do

**This pack never scrapes, crawls or automates TikTok**, and it does not drive
a browser on TikTok. TikTok's US Terms of Service (version of July 15, 2026), section 3.4, prohibit
using automated systems or software to scrape, crawl, export or extract data
or content from the platform, except as approved in writing by TikTok:
https://www.tiktok.com/legal/page/us/terms-of-service/en
(Terms differ by region and their section numbers may too; this pack cites
the US version.)

That cannot be worked around inside the rules, so this skill does not try.
`trends.py` only analyses snapshot files the user brings. **How the user
collects those snapshots is the user's choice and the user's responsibility.**
Automated collection from TikTok requires TikTok's written permission under its
Terms. This skill does not name, recommend or link any scraping tool or
extension, and will not help build one.

TikTok's own Research API is for approved academic and not-for-profit
researchers who are independent of commercial interests, so it is not a route
for a creator or a business:
https://developers.tiktok.com/products/research-api/

## The manual workflow

Do this once or twice a week, about ten minutes each time, and save each look
as a dated snapshot. Velocity needs at least two.

1. **TikTok Creative Center** (ads.tiktok.com/business/creativecenter). Open
   the Trends area and look at hashtags, songs and creators for the user's
   region and a 7-day window. Section names, filters and which data is shown
   change over time and by region, so they are unverified here; describe what
   you see rather than assuming.
2. **Copy the rows by hand** into `${CLAUDE_SKILL_DIR}/trends.csv` (a header
   only template): `captured_at` is today's date, `kind` is hashtag, sound,
   keyword, creator or format, then `name`, `rank`, and `posts` or `views` if
   shown. The extra columns (`why_it_fits_me`, `my_angle`, `use_by`, `notes`)
   are for the user's own planning and are ignored by the tool.
3. **The For You page**, for 10 minutes, logged in as the user, on their own
   phone. Note formats and sounds that repeat across unrelated creators. Add
   them as `kind` `format` or `sound` rows. Nothing is clicked, followed or
   liked on the user's behalf.
4. Save each look as its own file or append rows with the new date.

The full field list, header aliases and JSON shapes are in
`${CLAUDE_SKILL_DIR}/schema.md`.

## What trends.py reports

- **Velocity** between the two most recent snapshots: rank change per day,
  posts and views growth per day and as a percent.
- **Stage**: fading, emerging, rising, saturated, peaking or stalled,
  checked in that order. Any decline (rank falling, or posts or views
  shrinking) is fading first. Saturated means high volume with little growth;
  stalled means flat at low volume. The thresholds are printed on every run
  and every one is a flag (`--rising-pct`, `--peak-pct`, `--fading-pct`,
  `--saturated-posts`, `--emerging-days`, `--rank-rising`). They are this
  pack's defaults, not TikTok figures. Full rules in `schema.md`.
- **First seen**: the first snapshot date the trend appears in.
- **Niche fit** 0-100 against `--niche "kw1,kw2"` or the `Niche keywords:`
  line in `~/.claude/tiktok/voice.md` (`--voice` for another path).
- A trend in only one snapshot says **"one snapshot, no velocity"**.
- A trend missing from the newest snapshot of its kind and region is
  **"stale (last seen DATE)"** and never makes the shortlist.
- **Make this week**: up to five picks that are emerging, rising or peaking
  and fit the niche, each handed to `/tt-hook` then `/tt-script`.

## How to talk about the result

- A trend list is a sample of what was collected, on the days it was
  collected. Say how many snapshots it is based on.
- Check each pick in the app before filming. Trends move faster than weekly
  snapshots.
- Sounds: the user must have the right to use a sound on their account type.
  Business accounts may see a more limited music library (unverified for every
  region). Do not suggest using a sound the account cannot use.
- Never invent a trend, a rank or a growth figure.

Nothing is posted, followed, liked or commented by this skill.
