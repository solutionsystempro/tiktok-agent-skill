# Trend snapshot schema

`trends.py` reads one normalized shape. A snapshot is a set of rows captured
on one date. Several snapshots, in one file or several, are what make
velocity possible.

The pack does not collect these rows. You bring them. See the collection note
in `SKILL.md`.

## Fields

| field | required | type | notes |
| --- | --- | --- | --- |
| `captured_at` | yes | ISO date | `2026-10-08` or `2026-10-08T14:00:00Z`. `2026/10/08` is accepted. Time of day is ignored. |
| `kind` | yes | text | one of `hashtag`, `sound`, `keyword`, `creator`, `format` |
| `name` | yes | text | the hashtag, sound title, keyword, creator handle or format name. A leading `#` on hashtags and `@` on creators is ignored when matching across snapshots. |
| `rank` | no | integer | position in the list you copied, 1 is top |
| `views` | no | count | `412000`, `412,000`, `412K`, `1.2M` all work |
| `posts` | no | count | number of videos using it, same formats as views |
| `region` | no | text | country or market code, for example `US`. Rows are compared within a region. |
| `source` | no | text | where the row came from, in your words |
| `url` | no | text | a link for your own reference. Never fetched. |

Any other columns are ignored, so the template's planning columns
(`why_it_fits_me`, `my_angle`, `use_by`, `notes`) can sit in the same file.

A trend is identified by `kind` + `name` + `region`.

## Header aliases

Headers are matched case-insensitively, with spaces and hyphens read as
underscores.

| field | also accepted |
| --- | --- |
| `captured_at` | captured, capture_date, date, snapshot_date, snapshot, collected_at, collected, checked, date_checked, timestamp, day |
| `kind` | type, trend_type, category_type |
| `name` | trend, item, title, label, term |
| `rank` | ranking, position, pos, #, no, no. |
| `views` | video_views, view_count, plays, play_count, total_views |
| `posts` | post_count, videos, video_count, publish_count, uses, use_count |
| `region` | country, country_code, market, location |
| `source` | collector, origin |
| `url` | link, href |

If there is no `name` column but there is a column named `hashtag`,
`sound`, `song`, `music`, `audio`, `keyword`, `search_term`, `creator`,
`account`, `handle` or `format`, that column is the name and also sets the
kind. `--kind` sets a default kind for rows that have none.

A missing required column stops the run with the list of headers found. A
row with a bad date, an unknown kind or no name is skipped with a note on
stderr. Counts that are not numbers are treated as blank.

## CSV

UTF-8, with or without a BOM, CRLF or LF line endings. Comma, tab or
semicolon delimited.

```csv
captured_at,kind,name,rank,posts,region,source
2026-10-01,hashtag,#sourdoughtok,12,40K,US,creative center by hand
2026-10-08,hashtag,#sourdoughtok,6,70K,US,creative center by hand
```

## JSON

A list of row objects:

```json
[
  {"captured_at": "2026-10-01", "kind": "sound", "name": "Kitchen beat", "rank": 5, "posts": 20000}
]
```

or an object with `items`, `rows`, `data` or `trends` holding that list (a
top-level `captured_at` fills rows that lack one), or with `snapshots`:

```json
{"snapshots": [
  {"captured_at": "2026-10-01", "items": [{"kind": "hashtag", "name": "#sourdoughtok", "posts": 40000}]},
  {"captured_at": "2026-10-08", "items": [{"kind": "hashtag", "name": "#sourdoughtok", "posts": 70000}]}
]}
```

## How stages are decided

Growth is percent change per day between the two most recent snapshots of a
trend, using `posts` if both snapshots have it, otherwise `views`. Defaults,
each changeable with the flag in brackets. The rules are checked in this
order and the first match wins:

1. **fading**: the rank fell by at least 1 place per day (`--rank-rising`),
   or posts or views shrank faster than -1%/day (`--fading-pct`). A decline
   is checked first, so a falling rank is fading even when posts are flat.
2. **emerging**: growth at or above 5%/day (`--rising-pct`) and first seen
   within 7 days of the trend's own last sighting (`--emerging-days`). Each
   trend is judged on its own dates, so other rows in the file do not change
   it.
3. **rising**: growth at or above 5%/day, seen for longer than that
4. **saturated**: 1,000,000 posts or more (`--saturated-posts`) and growth
   below the rising line. High volume, little room left.
5. **peaking**: growth at or above 1%/day (`--peak-pct`), below the rising
   line, under the saturated post count
6. **stalled**: growth between -1% and 1%/day under the saturated post
   count. Flat at low volume; it never took off.

With rank only and no counts: falling at least 1 place per day is fading,
climbing at least that fast is rising or emerging, anything between is
peaking.

A trend found in only one snapshot is labelled `one snapshot` and shows "one
snapshot, no velocity".

A trend missing from the newest snapshot of its own kind and region is
labelled `stale (last seen DATE)`, whatever its stage was then, and is left
out of the "make this week" shortlist. Freshness is judged per kind and
region, so a sounds list captured a day after the hashtags list does not make
the hashtags stale.

These thresholds are this pack's defaults, not TikTok figures. Tune them to
your niche once you have a few weeks of snapshots.
