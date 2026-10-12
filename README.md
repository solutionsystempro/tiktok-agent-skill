# The TikTok agent skill

Twelve Claude skills for running a TikTok account. Free, MIT, no signup, no API
key, nothing to connect.

An original pack by Ian Ryan Kirk. Structure and several tools adapted from
Jake Schincariol's
[instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill).
See [Credit](#credit) for exactly which files.

**Nothing gets posted until you post it.** These skills write drafts and read
files you give them. You film, you post, you reply.

## Install

Paste this into Claude:

```
https://github.com/solutionsystempro/tiktok-agent-skill

Install this skill, then confirm /tt-hook works.
```

Or in Claude Code:

```bash
git clone https://github.com/solutionsystempro/tiktok-agent-skill.git
cp -r tiktok-agent-skill/skills/tt-* ~/.claude/skills/
```

On Windows, in PowerShell:

```powershell
git clone https://github.com/solutionsystempro/tiktok-agent-skill.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force tiktok-agent-skill\skills\tt-* "$HOME\.claude\skills\"
```

Or as a plugin:

```
/plugin marketplace add solutionsystempro/tiktok-agent-skill
/plugin install tiktok-agent
```

Copy all twelve folders together. `/tt-viral` reads `tt-hook/hooks.json` and
`tt-hook/hookscore.py` from its sibling folder.

Then fill in `templates/voice.md` and save it as `~/.claude/tiktok/voice.md`,
or give Claude three of your own TikTok transcripts and say "write my voice.md
from these". Every skill reads it.

## The twelve

| command | what it does |
| --- | --- |
| `/tt-hook` | The first one to three seconds as three layers: spoken line, on-screen text, first visual. 20 [hook formulas](skills/tt-hook/hooks.json), scored per layer by `hookscore.py`. |
| `/tt-script` | Short-form script and timed beat sheet from `beats.py`: hook beat under 3s, beat length, loop, length against your target. |
| `/tt-caption` | Caption and on-screen text linted by `caption.py`: 2,200 UTF-16 units, first-line preview, hashtags (heuristic guide), search terms, emoji. Cross-post pack for Shorts and Reels checked by `crosspost.py`. |
| `/tt-seo` | Keyword map from search suggestions you paste (`kwmap.py`), and question research that clusters pasted questions into script ideas (`questions.py`). No scraping. |
| `/tt-trends` | Manual Creative Center and For You page workflow, a CSV template, and `trends.py`, which analyses the snapshots you bring: velocity, stage, first seen, niche fit. |
| `/tt-retention` | Reads TikTok Studio analytics CSV exports with `retention.py`: hook leak, steepest drops, completion ranking. |
| `/tt-viral` | Ranks videos you collected by views over each account's median or followers, labelled per row, names the formula, and aggregates hook type, topic, length, structure and CTA, including what the top quartile shares. `swipe.py`. |
| `/tt-comment` | Reply drafts for comments you paste, plus reply-with-video ideas. You post each one by hand. |
| `/tt-repurpose` | A Reel, Short or long transcript rebuilt as a TikTok: new hook, length, cards, caption, plus the per-video cross-post pack. |
| `/tt-profile` | Profile scored against a [10-part rubric](skills/tt-profile/rubric.json) out of 100, then rewritten in fix-first order. |
| `/tt-plan` | The 30-day batch: 5 creators, their 10 best posts each, breakdown, question research, 30 scripts, a filming-day sheet for one 1 to 2 hour session, a posting calendar and a daily manual engagement checklist. |
| `/tt-human` | The humanizer. `humanize.py` strips slop, TikTok bait and invisible characters; `detect.py` scores what is left. |

## The 30-day batch

`/tt-plan` is the backbone. One month, researched and written in one sitting
and filmed in one session:

1. you list the top 5 creators in your niche
2. you collect each one's 10 best-performing posts, a 50-row swipe file
3. `/tt-viral` breaks the 50 posts down: hook types, topics, structures,
   CTAs, median length, and what the top quartile has in common
4. `/tt-seo` clusters the questions people ask into script ideas
5. `/tt-hook` and `/tt-script` write 30 scripts, `/tt-caption` the captions
   and cross-post packs, `/tt-human` cleans all of it
6. a filming-day sheet groups the 30 by set, outfit and location, with a shot
   list and on-screen text per script, to fit one 1 to 2 hour session
7. a 30-day posting calendar
8. a daily engagement checklist that you do by hand

Everything lands in `~/.claude/tiktok/month-YYYY-MM/`. The template is
[`templates/month.md`](templates/month.md).

## The tools

Standard library only, tested on Python 3.12, no network. The examples use
`python`; on macOS or Linux that may be `python3`. Inside Claude Code the
skills call them as `python "${CLAUDE_SKILL_DIR}/tool.py"`.

```bash
python skills/tt-hook/hookscore.py hooks.txt
python skills/tt-script/beats.py script.txt --target 30
python skills/tt-caption/caption.py caption.txt --keywords "sourdough starter" --onscreen cards.txt
python skills/tt-seo/kwmap.py pasted.txt --seed sourdough
python skills/tt-seo/questions.py questions.txt --seed sourdough
python skills/tt-caption/crosspost.py pack.txt
python skills/tt-trends/trends.py week1.csv week2.csv --niche "sourdough,bread"
python skills/tt-retention/retention.py export.csv
python skills/tt-viral/swipe.py captured.tsv --out ~/.claude/tiktok/swipe.md
python skills/tt-human/humanize.py draft.txt --report
python skills/tt-human/detect.py draft.txt
```

A three-layer hook file looks like this:

```
spoken: This chair cost $1,400. Here is what it buys you.
text: $1,400 CHAIR. WORTH IT?
visual: Hand slaps the price sticker onto the chair.
```

```
HOOK RANKING  (spoken / on-screen / visual)
==============================================================================
->  89.7 STRONG [ 85 100 100]  This chair cost $1,400. Here is what it buys you.
    16.6 WEAK   [ 37   -   -]  POV: you said yes to helping a friend move
        missing: ON-SCREEN, VISUAL
     0.4 WEAK   [ 23  46  43]  Hey guys, today I wanted to talk about chairs
        dealbreaker: Greeting. The first second is too expensive to spend on hello.
        dealbreaker: Static opener: the first frame is a still face waiting to talk.
```

The scores are local heuristics. None of the weights were fitted to TikTok
performance data, and no tool here predicts views.

## Rules this pack keeps

**No scraping, no unofficial APIs, no browser automation of TikTok, no
scraping services.** TikTok's US Terms of Service (version of July 15, 2026), section 3.4, prohibit
using automated systems or software to scrape, crawl, export or extract data
or content from the platform, except as approved in writing by TikTok:
<https://www.tiktok.com/legal/page/us/terms-of-service/en>. Data in this pack
comes from four places only: your own TikTok Studio exports, things you paste,
TikTok Creative Center viewed by hand, or official APIs you set up yourself.
`trends.py` analyses snapshot files you bring; how you collect them is your
choice and your responsibility, and automated collection from TikTok needs
TikTok's written permission.

**Nothing is posted, commented, DMed, liked or followed by this pack.** Every
outbound item, a caption, a reply, a script, is a draft a human reviews and
sends, one at a time. There is no auto-reply and no scheduler.

**Nothing is invented.** No made-up statistics, studies, benchmarks or
results. A draft that needs a number you have not given comes back with
`{{your number}}` and a flag.

## The official APIs, accurately

| API | what it is for | the catch |
| --- | --- | --- |
| [Content Posting API](https://developers.tiktok.com/doc/content-posting-api-get-started/) | an app you authorize posts to your account | TikTok's [content sharing guidelines](https://developers.tiktok.com/doc/content-sharing-guidelines/) require your express consent before content is uploaded and say apps should show a preview first. Content from unaudited apps is restricted to private viewing (`SELF_ONLY`) until the app passes an audit. The caption field allows 2,200 UTF-16 units ([reference](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post/)). |
| [YouTube Data API](https://developers.google.com/youtube/v3/docs/videos) | not TikTok; cited because `crosspost.py` checks Shorts titles (100 characters) and descriptions (5,000 bytes) against it | neither field may contain `<` or `>` |
| [Display API](https://developers.tiktok.com/doc/display-api-get-started/) | your own profile and your own public videos, with fields such as `view_count` and `duration` ([video object](https://developers.tiktok.com/doc/tiktok-api-v2-video-object/)) | needs Login Kit and your OAuth consent with the `user.info.basic` and `video.list` scopes. Your account only, not competitors'. No retention fields are documented. |
| [Research API](https://developers.tiktok.com/products/research-api/) | public data for research | for approved academic and not-for-profit researchers independent of commercial interests. Not a route for creators or businesses. |

This pack does not ship an app for any of them.

## What is not verified

Platform numbers change. These are marked unverified wherever they appear, and
the tools do not treat them as rules:

- maximum video length for recording and upload
- any hashtag count limit (the caption linter's "up to 5" is a heuristic)
- where the caption preview is cut
- the in-app caption limit, if it differs from the API's 2,200 UTF-16 units
- bio length, link-in-bio eligibility, number of pinned videos, playlists
- which TikTok Studio views can be exported, and their column names
- Creative Center section names and the data each shows
- the music library available to business accounts
- the Instagram Reels caption and hashtag limits used by `crosspost.py`
  (taken from instagram-agent-skill, not re-verified here)

If something here contradicts what TikTok does when you read it, TikTok is
right. Please open an issue.

## Files

```
skills/tt-hook/hooks.json          20 hook formulas, three layers each, with match regexes
skills/tt-hook/hookscore.py        three-layer hook scorer
skills/tt-script/beats.py          script to timed beat sheet
skills/tt-caption/caption.py       caption and on-screen text linter
skills/tt-caption/crosspost.py     TikTok / Shorts / Reels cross-post pack checker
skills/tt-seo/kwmap.py             keyword map from pasted phrases
skills/tt-seo/questions.py         question clusters to script ideas
skills/tt-trends/trends.py         snapshot analyser: velocity, stage, first seen, niche fit
skills/tt-trends/schema.md         the normalized snapshot schema and stage rules
skills/tt-trends/trends.csv        header-only template for manual snapshots
skills/tt-retention/retention.py   TikTok Studio export reader
skills/tt-viral/swipe.py           swipe-file ranker and breakdown aggregation
skills/tt-viral/swipe.tsv          header-only template for the swipe file
skills/tt-profile/rubric.json      the 100-point profile rubric
skills/tt-human/slop.json          lexicon: 165 terms, 18 invisible classes, 19 tells
skills/tt-human/humanize.py        cleaning passes
skills/tt-human/detect.py          five-check panel
templates/voice.md                 your voice profile. Fill this in first.
templates/month.md                 the 30-day batch folder template
tests/                             stdlib unittest suite
```

## Tests

From the repo root:

```bash
python -m unittest discover -s tests -v
```

No dependencies. Covers each tool's main path and edge cases: empty input,
emoji and UTF-16 counting, BOM, CRLF, malformed counts, mixed baselines,
missing columns, trend velocity and stage edges, swipe breakdown
aggregation, question clustering, cross-post limits, plus repo checks (manifests
parse, versions agree, the README lists exactly the skills that exist).

## Credit

An original pack by Ian Ryan Kirk.

Structure and several tools adapted from Jake Schincariol's
[instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill)
(MIT). Adapted files carry a header saying so: `hookscore.py`, `beats.py`,
`caption.py`, `swipe.py`, `retention.py`, `humanize.py`, `detect.py` and
`slop.json`. The layout, the `SKILL.md` conventions and the voice template
follow the same pack. The hook formulas, rubric, `trends.py`, `kwmap.py`,
`questions.py`, `crosspost.py`, the month template and the skill texts are
new. Jake's MIT notice is reproduced in [LICENSE](LICENSE).

## License

MIT, see [LICENSE](LICENSE).
