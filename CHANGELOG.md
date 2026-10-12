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

### Tests

Standard-library `unittest` suite for every tool plus repo checks.
