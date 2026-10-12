---
name: tt-retention
description: >-
  Read a TikTok Studio analytics CSV export with retention.py and find where
  viewers leave: hook leak in the first 3 seconds, steepest drops, when the
  curve crosses 50% and 25%, or a per-video ranking by watched-full-video
  and average watch time. Use when the user shares TikTok Studio analytics,
  asks why viewers stop watching their TikToks, or has a TikTok retention
  export.
license: MIT
metadata:
  maintainer: Ian Ryan Kirk
---

# tt-retention

```bash
python "${CLAUDE_SKILL_DIR}/retention.py" export.csv
python "${CLAUDE_SKILL_DIR}/retention.py" export.csv --json
python "${CLAUDE_SKILL_DIR}/retention.py" curve.csv --ratio     # or --percent
```

`${CLAUDE_SKILL_DIR}` is this skill's folder. On macOS or Linux, use `python3`
if `python` is not found.

## Getting the data

From the user's own account only. TikTok Studio (in the app, or on desktop)
shows per-video analytics such as average watch time, watched full video and a
retention chart. Which of these can be downloaded as a file, from which
screen, and with which column names, is **unverified** and has changed over
time. Ask the user what they can export. If there is no download:

- Copy the per-video numbers by hand into a CSV with the headers
  `Video title, Video views, Average watch time, Watched full video, Duration`.
- Or read the retention chart and type a few points into a two-column CSV:
  `Time, Viewers (%)`. Ten points is enough to find the hook leak and the
  biggest drop.

The official Display API returns a user's own public videos with fields such
as `view_count` and `duration` after the user authorizes an app through Login
Kit with the `user.info.basic` and `video.list` scopes. It does not document
retention fields:
https://developers.tiktok.com/doc/display-api-get-started/ and
https://developers.tiktok.com/doc/tiktok-api-v2-video-object/

## How the file is read

Columns are found by header name, not position, so reordering and extra
columns are fine. Two shapes:

- **Curve**: a time column (`Time`, `Second`, `Position`, ...) and a retention
  column (`Retention`, `Viewers (%)`, `Audience retention`, ...). Times can be
  `3`, `3s`, `0:03` or `00:00:03`.
- **Summary**: one row per video with `Average watch time` and/or `Watched
  full video`, optionally `Video views`, `Duration`, `Title`.

If neither shape is found, the tool stops and lists the headers it saw and the
names it accepts. Rename a header and run again. A retention or completion
column with `%` or `percent` in its header is read as percent, `ratio` as 0-1;
otherwise the values decide and a note says so.

## What to hand back

- **Curve**: the hook leak (points lost by second 3), the steepest drops with
  their times, and when the curve falls below 50% and 25%. Name the single
  biggest leak and one change for it. If it is the hook, send the user to
  `/tt-hook`. If it is a cliff mid-video, ask what was on screen at that
  second.
- **Summary**: which videos sit furthest above and below the batch median on
  completion, and which to open in Studio to see their curves.

The thresholds (3-second hook window, a drop of 2 points per second counts as
a cliff) are this tool's heuristics. Do not compare the user's numbers to
"average TikTok retention": there is no verified benchmark, and inventing one
is the thing this pack does not do.

Nothing here posts or changes anything on TikTok.
