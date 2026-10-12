#!/usr/bin/env python3
# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
"""
trends.py - analyse TikTok trend snapshots you bring, across several dates.

This tool never connects to TikTok. It reads files you already have: rows you
copied by hand from TikTok Creative Center, a CSV from whatever collector you
chose, or JSON from your own tooling. How you collected them is your choice
and your responsibility. The normalized schema is in schema.md next to this
file.

For each trend (kind + name + region) it reports:
  VELOCITY    rank change and posts / views growth per day between the two
              most recent snapshots
  STAGE       emerging / rising / peaking / saturated / stalled / fading, from growth
              thresholds that are printed with every run and can be changed
  FIRST SEEN  the earliest snapshot date it appears in
  NICHE FIT   0-100 against your niche keywords (--niche, or the
              "Niche keywords:" line in your voice.md)

A trend seen in only one snapshot is marked "one snapshot, no velocity". One
reading cannot show direction.

Usage
  python trends.py week1.csv week2.csv
  python trends.py snapshots.json --niche "sourdough,bread,baking"
  python trends.py *.csv --kind hashtag --top 5 --markdown
  python trends.py a.csv b.csv --json
  python trends.py a.csv b.csv --rising-pct 8 --saturated-posts 500000
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import date, datetime

KINDS = ("hashtag", "sound", "keyword", "creator", "format")
REQUIRED = ("captured_at", "kind", "name")
FIELDS = ("captured_at", "kind", "name", "rank", "views", "posts", "region", "source", "url")

ALIASES = {
    "captured_at": ["captured_at", "captured", "capture_date", "date", "snapshot_date",
                    "snapshot", "collected_at", "collected", "checked", "date_checked",
                    "timestamp", "day"],
    "kind": ["kind", "type", "trend_type", "category_type"],
    "name": ["name", "trend", "item", "title", "label", "term"],
    "rank": ["rank", "ranking", "position", "pos", "#", "no", "no."],
    "views": ["views", "video_views", "view_count", "plays", "play_count", "total_views"],
    "posts": ["posts", "post_count", "videos", "video_count", "publish_count", "uses",
              "use_count"],
    "region": ["region", "country", "country_code", "market", "location"],
    "source": ["source", "collector", "origin"],
    "url": ["url", "link", "href"],
}
# A column named after the kind doubles as the name column and sets the kind.
KIND_COLUMNS = {
    "hashtag": "hashtag", "hashtags": "hashtag", "tag": "hashtag",
    "sound": "sound", "sounds": "sound", "song": "sound", "songs": "sound",
    "music": "sound", "audio": "sound",
    "keyword": "keyword", "keywords": "keyword", "search_term": "keyword",
    "creator": "creator", "creators": "creator", "account": "creator", "handle": "creator",
    "format": "format", "formats": "format",
}
KIND_VALUES = dict(KIND_COLUMNS, **{k: k for k in KINDS})

THRESHOLDS = {
    "rising_pct": 5.0,          # growth % per day at or above this is rising
    "peak_pct": 1.0,            # at or above this (and below rising) is peaking
    "fading_pct": -1.0,         # below this is fading
    "saturated_posts": 1_000_000,  # this many posts or more, growing below rising: saturated
    "emerging_days": 7,         # rising, and first seen within this many days of its own last sighting
    "rank_rising": 1.0,         # rank-only data: places climbed per day for rising
}
STAGE_WEIGHT = {"emerging": 4, "rising": 3, "peaking": 2, "saturated": 1, "stalled": 1,
                "fading": 0, "one snapshot": 1}


def norm_header(h):
    h = (h or "").replace("﻿", "").strip().lower()
    return re.sub(r"[\s\-]+", "_", h)


def map_columns(headers):
    """Returns ({field: column index}, implied_kind or None)."""
    names = [norm_header(h) for h in headers]
    cols, implied = {}, None
    for field, aliases in ALIASES.items():
        for alias in aliases:
            if alias in names:
                cols[field] = names.index(alias)
                break
    if "name" not in cols:
        for i, n in enumerate(names):
            if n in KIND_COLUMNS:
                cols["name"], implied = i, KIND_COLUMNS[n]
                break
    return cols, implied


def parse_count(value):
    """'412000', '412,000', '412K', '1.2M', 1200 -> int; blank or junk -> None."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    s = str(value).strip().lower().replace(" ", "").replace(" ", "")
    if not s:
        return None
    m = re.fullmatch(r"(\d+)[.,](\d{1,2})([kmb])", s)
    if m:
        num, suffix = float(m.group(1) + "." + m.group(2)), m.group(3)
    else:
        m = re.fullmatch(r"(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?([kmb]?)", s)
        if not m:
            return None
        num = float(m.group(1).replace(",", "") + ("." + m.group(2) if m.group(2) else ""))
        suffix = m.group(3)
    return int(round(num * {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[suffix]))


def parse_date(value):
    s = str(value or "").strip()
    if not s:
        return None
    s = s.replace("/", "-")
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def name_key(kind, name):
    n = re.sub(r"\s+", " ", (name or "").strip().lower())
    if kind == "hashtag":
        n = n.lstrip("#")
    if kind == "creator":
        n = n.lstrip("@")
    return n


def normalise(raw, label, implied_kind=None, default_kind=None, notes=None):
    """One raw dict -> a normalized row, or None with a note."""
    row = {f: raw.get(f) for f in FIELDS}
    kind = str(row["kind"] or implied_kind or default_kind or "").strip().lower()
    kind = KIND_VALUES.get(kind, kind)
    when = parse_date(row["captured_at"])
    name = str(row["name"] or "").strip()
    problem = None
    if not name:
        problem = "no name"
    elif when is None:
        problem = f"captured_at \"{row['captured_at']}\" is not an ISO date (YYYY-MM-DD)"
    elif kind not in KINDS:
        problem = f"kind \"{kind}\" is not one of {', '.join(KINDS)}"
    if problem:
        if notes is not None:
            notes.append(f"{label}: skipped, {problem}")
        return None
    return {
        "captured_at": when, "kind": kind, "name": name, "key": name_key(kind, name),
        "rank": parse_count(row["rank"]), "views": parse_count(row["views"]),
        "posts": parse_count(row["posts"]),
        "region": str(row["region"] or "").strip().upper(),
        "source": str(row["source"] or "").strip(), "url": str(row["url"] or "").strip(),
    }


def missing_error(fields, headers, source, implied_or_default):
    need = [f for f in REQUIRED if f not in fields and not (f == "kind" and implied_or_default)]
    if need:
        found = ", ".join(f"\"{h}\"" for h in headers) or "none"
        raise ValueError(
            f"{source}: missing required column(s): {', '.join(need)}. Found: {found}. "
            f"Accepted names for each are listed in schema.md (for example captured_at: "
            f"{', '.join(ALIASES['captured_at'][:4])}). For kind, a column named "
            f"'hashtag', 'sound', 'keyword' or 'creator' works, or pass --kind.")


def read_csv(text, source, default_kind=None, notes=None):
    sample = "\n".join(text.split("\n")[:10])
    delim = "\t" if sample.count("\t") > sample.count(",") else (
        ";" if sample.count(";") > sample.count(",") else ",")
    table = [r for r in csv.reader(io.StringIO(text), delimiter=delim) if any(c.strip() for c in r)]
    if not table:
        return []
    headers = table[0]
    cols, implied = map_columns(headers)
    missing_error(cols, [h.strip() for h in headers], source, implied or default_kind)
    out = []
    for n, cells in enumerate(table[1:], 2):
        raw = {f: (cells[i] if i < len(cells) else "") for f, i in cols.items()}
        r = normalise(raw, f"{source} line {n}", implied, default_kind, notes)
        if r:
            out.append(r)
    return out


def read_json(text, source, default_kind=None, notes=None):
    data = json.loads(text)
    batches = []                    # (rows, captured_at default)
    if isinstance(data, list):
        batches.append((data, None))
    elif isinstance(data, dict):
        if isinstance(data.get("snapshots"), list):
            for snap in data["snapshots"]:
                batches.append((snap.get("items") or snap.get("rows") or [],
                                snap.get("captured_at")))
        else:
            for key in ("items", "rows", "data", "trends"):
                if isinstance(data.get(key), list):
                    batches.append((data[key], data.get("captured_at")))
                    break
    if not batches:
        raise ValueError(f"{source}: JSON must be a list of rows, or an object with "
                         "'items' / 'rows' / 'data' / 'snapshots'")
    out, n = [], 0
    for rows, when in batches:
        for item in rows:
            n += 1
            if not isinstance(item, dict):
                if notes is not None:
                    notes.append(f"{source} item {n}: skipped, not an object")
                continue
            headers = list(item.keys())
            cols, implied = map_columns(headers)
            raw = {f: item[headers[i]] for f, i in cols.items()}
            if when and not raw.get("captured_at"):
                raw["captured_at"] = when
            if n == 1:
                fields = set(cols) | ({"captured_at"} if when else set())
                missing_error(fields, headers, source, implied or default_kind)
            r = normalise(raw, f"{source} item {n}", implied, default_kind, notes)
            if r:
                out.append(r)
    return out


def load(path_or_text, source=None, default_kind=None, notes=None, is_text=False):
    if is_text:
        text = path_or_text
    else:
        source = source or path_or_text
        with open(path_or_text, encoding="utf-8-sig", newline="") as fh:
            text = fh.read()
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise ValueError(f"{source}: the file is empty")
    if text.lstrip()[:1] in "[{":
        return read_json(text, source, default_kind, notes)
    return read_csv(text, source, default_kind, notes)


# ------------------------------------------------------------------ analysis

def niche_keywords_from_voice(path):
    try:
        with open(os.path.expanduser(path), encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError:
        return []
    m = re.search(r"(?im)^\W*niche keywords\W*:\**[ \t]*(.*)$", text)
    if not m:
        return []
    # The template's "(comma-separated, for example: ...)" hint is not a keyword.
    value = re.sub(r"\([^)]*\)?", "", m.group(1))
    return [k.strip(" .*`") for k in value.split(",") if k.strip(" .*`")]


def niche_fit(name, keywords):
    """100 if a keyword appears whole in the name (spaces ignored, so
    'sourdough bread' matches #sourdoughbread), 60 if a word of 3+ letters
    from a keyword does, else 0."""
    if not keywords:
        return None
    compact = re.sub(r"[^\w]", "", name.lower())
    best = 0
    for k in keywords:
        kc = re.sub(r"[^\w]", "", k.lower())
        if kc and kc in compact:
            return 100
        if any(len(t) >= 3 and t in compact for t in re.findall(r"\w+", k.lower())):
            best = 60
    return best


def growth_pct(prev, last, days):
    if prev is None or last is None or not days:
        return None
    if prev == 0:
        return None
    return (last - prev) / prev * 100 / days


def stage_for(g, rank_per_day, posts, first_seen, last_seen, t, views_g=None):
    """Stage from growth % per day g (posts, else views), else from rank.

    Order matters. Any decline is checked first: a rank falling by at least
    rank_rising places a day, or posts or views shrinking faster than
    fading_pct, is "fading" whatever the other numbers say. Only then growth:
    rising / emerging, then saturated (high volume, below the rising line),
    peaking (slowing growth), and stalled (flat at low volume)."""
    if g is None and rank_per_day is None:
        return None
    if rank_per_day is not None and rank_per_day <= -t["rank_rising"]:
        return "fading"
    if any(x is not None and x < t["fading_pct"] for x in (g, views_g)):
        return "fading"
    new = (last_seen - first_seen).days <= t["emerging_days"]
    if g is not None:
        if g >= t["rising_pct"]:
            return "emerging" if new else "rising"
        if posts is not None and posts >= t["saturated_posts"]:
            return "saturated"
        if g >= t["peak_pct"]:
            return "peaking"
        return "stalled"
    if rank_per_day >= t["rank_rising"]:
        return "emerging" if new else "rising"
    return "peaking"


def analyse(rows, keywords=None, thresholds=None):
    t = dict(THRESHOLDS, **(thresholds or {}))
    if not rows:
        return {"trends": [], "thresholds": t, "snapshots": [], "keywords": keywords or []}
    latest = max(r["captured_at"] for r in rows)
    # Freshness is judged per kind and region, so a sounds list captured a
    # day after the hashtags list does not make every hashtag stale.
    newest = {}
    for r in rows:
        k = (r["kind"], r["region"])
        newest[k] = max(newest.get(k, r["captured_at"]), r["captured_at"])
    groups = {}
    for r in rows:
        groups.setdefault((r["kind"], r["key"], r["region"]), {})[r["captured_at"]] = r
    trends = []
    for (kind, key, region), by_date in groups.items():
        dates = sorted(by_date)
        last = by_date[dates[-1]]
        item = {
            "kind": kind, "name": last["name"], "region": region,
            "first_seen": dates[0].isoformat(), "last_seen": dates[-1].isoformat(),
            "snapshots": len(dates), "rank": last["rank"], "views": last["views"],
            "posts": last["posts"], "url": last["url"], "source": last["source"],
            "rank_change_per_day": None, "posts_per_day": None, "posts_growth_pct": None,
            "views_per_day": None, "views_growth_pct": None,
        }
        if len(dates) < 2:
            item["stage"] = "one snapshot"
            item["velocity"] = "one snapshot, no velocity"
        else:
            prev = by_date[dates[-2]]
            days = (dates[-1] - dates[-2]).days
            if prev["rank"] is not None and last["rank"] is not None:
                item["rank_change_per_day"] = round((prev["rank"] - last["rank"]) / days, 2)
            for f in ("posts", "views"):
                if prev[f] is not None and last[f] is not None:
                    item[f"{f}_per_day"] = round((last[f] - prev[f]) / days, 1)
                    g = growth_pct(prev[f], last[f], days)
                    item[f"{f}_growth_pct"] = round(g, 2) if g is not None else None
            g = item["posts_growth_pct"] if item["posts_growth_pct"] is not None \
                else item["views_growth_pct"]
            item["stage"] = stage_for(g, item["rank_change_per_day"], last["posts"],
                                      dates[0], dates[-1], t,
                                      views_g=item["views_growth_pct"]) or "one snapshot"
            item["velocity"] = f"over {days} day(s), {dates[-2]} to {dates[-1]}"
            if item["stage"] == "one snapshot":
                item["velocity"] = "no comparable rank, posts or views between snapshots"
        item["stale"] = dates[-1] < newest[(kind, region)]
        if item["stale"]:
            # Not in the newest snapshot of its own list: whatever it was doing
            # then, it is not evidence about this week.
            item["stage_when_last_seen"] = item["stage"]
            item["stage"] = f"stale (last seen {dates[-1].isoformat()})"
        item["fit"] = niche_fit(item["name"], keywords)
        growth = item["posts_growth_pct"] if item["posts_growth_pct"] is not None \
            else (item["views_growth_pct"] or 0)
        item["priority"] = round(STAGE_WEIGHT.get(item["stage"], 0) * 25
                                 + (item["fit"] or 0) * 0.5
                                 + max(-10, min(10, growth or 0)), 1)
        trends.append(item)
    trends.sort(key=lambda x: (-x["priority"], x["rank"] if x["rank"] is not None else 1e9,
                               x["name"].lower()))
    return {
        "trends": trends, "thresholds": t, "keywords": keywords or [],
        "snapshots": sorted({r["captured_at"].isoformat() for r in rows}),
        "latest": latest.isoformat(),
    }


def shortlist(a, n=5):
    good = {"emerging", "rising", "peaking"}
    picks = [x for x in a["trends"] if x["stage"] in good and not x.get("stale")
             and (x["fit"] is None or x["fit"] >= 60)]
    return picks[:n]


# ------------------------------------------------------------------ output

def fmt(n):
    if n is None:
        return "-"
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:g}"


def by_kind(a, kind_filter=None, top=10):
    out = {}
    for x in a["trends"]:
        if kind_filter and x["kind"] != kind_filter:
            continue
        lst = out.setdefault(x["kind"], [])
        if len(lst) < top:
            lst.append(x)
    return out


def threshold_line(t):
    return (f"fading first: rank down >= {t['rank_rising']} places/day or posts/views < "
            f"{t['fading_pct']}%/day; then rising >= {t['rising_pct']}%/day (emerging if first "
            f"seen within {t['emerging_days']} days of its last sighting), saturated = {fmt(t['saturated_posts'])}+ "
            f"posts below rising, peaking >= {t['peak_pct']}%/day, stalled = flat at lower "
            f"volume; rank-only rising >= {t['rank_rising']} places/day")


def render(a, kind_filter=None, top=10, out=sys.stdout):
    print(f"\nTREND SNAPSHOTS  ·  {len(a['snapshots'])} date(s): "
          f"{', '.join(a['snapshots'])}  ·  {len(a['trends'])} trends", file=out)
    print("=" * 92, file=out)
    print(f"  stages: {threshold_line(a['thresholds'])}", file=out)
    print(f"  niche keywords: {', '.join(a['keywords']) or 'none given, fit not scored'}",
          file=out)
    for kind, items in by_kind(a, kind_filter, top).items():
        print(f"\n  {kind.upper()}", file=out)
        print(f"  {'stage':<13}{'fit':>4}  {'rank':>5} {'d rank/d':>8} {'posts':>8} "
              f"{'posts %/d':>9}  {'first seen':<10}  name", file=out)
        for x in items:
            fit = "-" if x["fit"] is None else str(x["fit"])
            rcd = "-" if x["rank_change_per_day"] is None else f"{x['rank_change_per_day']:+g}"
            gp = "-" if x["posts_growth_pct"] is None else f"{x['posts_growth_pct']:+.1f}"
            region = f" [{x['region']}]" if x["region"] else ""
            print(f"  {x['stage'][:13]:<13}{fit:>4}  {fmt(x['rank']):>5} {rcd:>8} "
                  f"{fmt(x['posts']):>8} {gp:>9}  {x['first_seen']:<10}  "
                  f"{x['name'][:34]}{region}", file=out)
            if x["stage"] == "one snapshot":
                print(f"  {'':<13}     {x['velocity']}", file=out)
            if x.get("stale"):
                print(f"  {'':<13}     {x['stage']}, not in the newest {x['kind']} snapshot; "
                      "left out of MAKE THIS WEEK", file=out)
    picks = shortlist(a)
    print("\n  MAKE THIS WEEK", file=out)
    if not picks:
        print("    nothing emerging, rising or peaking that fits the niche. Collect another "
              "snapshot in a few days.", file=out)
    for x in picks:
        print(f"    {x['kind']:<8} {x['name'][:40]:<40} {x['stage']}"
              + (f", fit {x['fit']}" if x["fit"] is not None else ""), file=out)
        print(f"             -> /tt-hook three hooks on \"{x['name']}\" in your niche, "
              "then /tt-script", file=out)
    print("\n  A trend list is a sample of what someone chose to collect. Check each pick "
          "on TikTok\n  itself before filming, and use only sounds your account is allowed "
          "to use.\n", file=out)


def to_markdown(a, kind_filter=None, top=10):
    lines = ["# TikTok trend analysis", "",
             f"Snapshots: {', '.join(a['snapshots'])}", "",
             f"Stage thresholds: {threshold_line(a['thresholds'])}", ""]
    for kind, items in by_kind(a, kind_filter, top).items():
        lines += [f"## {kind}", "",
                  "| stage | fit | rank | rank change/day | posts | posts %/day | first seen | name |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for x in items:
            lines.append(
                f"| {x['stage']} | {'-' if x['fit'] is None else x['fit']} | {fmt(x['rank'])} | "
                f"{'-' if x['rank_change_per_day'] is None else x['rank_change_per_day']} | "
                f"{fmt(x['posts'])} | "
                f"{'-' if x['posts_growth_pct'] is None else x['posts_growth_pct']} | "
                f"{x['first_seen']} | {x['name'].replace('|', '/')} |")
        lines.append("")
    lines += ["## Make this week", ""]
    picks = shortlist(a)
    if not picks:
        lines.append("Nothing emerging, rising or peaking that fits the niche.")
    for x in picks:
        lines.append(f"- **{x['name']}** ({x['kind']}, {x['stage']}). Next: `/tt-hook` "
                     "for three hooks, then `/tt-script`.")
    return "\n".join(lines) + "\n"


def to_json(a, kind_filter=None, top=10):
    return {
        "snapshots": a["snapshots"], "thresholds": a["thresholds"], "keywords": a["keywords"],
        "by_kind": by_kind(a, kind_filter, top),
        "make_this_week": [x["name"] for x in shortlist(a)],
    }


def main():
    ap = argparse.ArgumentParser(description="Analyse TikTok trend snapshots you collected.")
    ap.add_argument("inputs", nargs="+", help="CSV or JSON snapshot files (see schema.md)")
    ap.add_argument("--niche", help="comma-separated niche keywords")
    ap.add_argument("--voice", default="~/.claude/tiktok/voice.md",
                    help="voice.md to read 'Niche keywords:' from when --niche is not given")
    ap.add_argument("--kind", choices=KINDS,
                    help="only show this kind; also the default kind for rows without one")
    ap.add_argument("--top", type=int, default=10, help="rows per kind (default 10)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    for key, val in THRESHOLDS.items():
        ap.add_argument("--" + key.replace("_", "-"), type=float, default=val,
                        help=f"stage threshold (default {val})")
    args = ap.parse_args()

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):   # Windows pipes default to cp1252
            stream.reconfigure(encoding="utf-8", errors="replace")
    keywords = ([k.strip() for k in args.niche.split(",") if k.strip()] if args.niche
                else niche_keywords_from_voice(args.voice))
    notes, rows = [], []
    try:
        for path in args.inputs:
            rows += load(path, default_kind=args.kind, notes=notes)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
    for n in notes:
        print(f"note: {n}", file=sys.stderr)
    if not rows:
        print("error: no usable rows. Each row needs captured_at, kind and name "
              "(see schema.md).", file=sys.stderr)
        sys.exit(2)
    thresholds = {k: getattr(args, k) for k in THRESHOLDS}
    a = analyse(rows, keywords, thresholds)
    if args.json:
        print(json.dumps(to_json(a, args.kind, args.top), indent=2, ensure_ascii=False))
    elif args.markdown:
        sys.stdout.write(to_markdown(a, args.kind, args.top))
    else:
        render(a, args.kind, args.top)


if __name__ == "__main__":
    main()
