# Changelog

## 1.0.0

First release, by Ian Ryan Kirk.

### Skills

Twelve: `tt-hook`, `tt-script`, `tt-caption`, `tt-seo`, `tt-trends`,
`tt-retention`, `tt-viral`, `tt-comment`, `tt-repurpose`, `tt-profile`,
`tt-human`, `tt-plan`.

### Tools

- `hookscore.py`: scores a hook as three layers (spoken, on-screen, first
  visual). The spoken checks are adapted from the instagram-agent-skill hook
  scorer; the on-screen and visual layers are new.
- `hooks.json`: 20 hook formulas written for this pack, each with a spoken
  template, on-screen line, first visual and match regex.
- `beats.py`: adapted from instagram-agent-skill. Adds bracketed direction
  lines that take no time, CRLF and BOM handling, and rejects non-finite
  `--wpm` and `--target`.
- `caption.py`: adapted from instagram-agent-skill, rebuilt for TikTok. Counts
  the 2,200 limit in UTF-16 units (Content Posting API), counts emoji as
  graphemes, labels the hashtag guide as a heuristic, checks search terms in
  the caption, the visible line and the on-screen cards.
- `kwmap.py`: new. Keyword map from pasted search phrases.
- `trends.py`: new. Analyses trend snapshots the user brings (CSV or JSON, one
  schema with header aliases): velocity, stage with printed and configurable
  thresholds, first seen, niche fit, and a "make this week" shortlist.
- `retention.py`: reads TikTok Studio CSV exports by header name, curve or
  per-video summary, with clear errors when columns are missing. Follows the
  header-based scale detection used in the YouTube companion pack.
- `swipe.py`: adapted from instagram-agent-skill. Accepts TSV or CSV, parses
  `1,2M` and `12.5k views`, reports malformed counts instead of guessing, and
  labels the baseline per row.
- `humanize.py`, `detect.py`, `slop.json`: adapted from instagram-agent-skill,
  with a TikTok block of phrases and structural tells. `humanize.py` also no
  longer leaves "tools.!" when a deleted closer ended in "!" or "?".

### 30-day batch workflow

- `tt-plan` is a 30-day batch: five creators, ten best posts each as a
  50-row swipe file, breakdown, question research, 30 scripts, a filming-day
  sheet grouped by set, outfit and location for one 1 to 2 hour session, a
  30-day calendar and a daily engagement checklist the user does by hand.
  Output goes in `~/.claude/tiktok/month-YYYY-MM/`, from `templates/month.md`.
- `swipe.py`: breakdown columns (`hook_type`, `topic`, `length_s`,
  `structure`, `cta`) with header aliases, and an aggregation across the
  batch: most common values, median length, and what the top quartile by
  outperformance shares more than the batch. `swipe.tsv` header template.
- `questions.py`: new. Clusters pasted questions by shared topic word and
  maps each cluster to script ideas.
- `crosspost.py`: new. Checks a per-video pack: TikTok caption (2,200 UTF-16
  units), Shorts title (100 characters) and description (5,000 bytes) from
  the YouTube Data API, and Reels caption (2,200 characters, 5 hashtags, as in
  instagram-agent-skill, unverified here).

### Tests

Standard-library `unittest` suite for every tool plus repo checks.
