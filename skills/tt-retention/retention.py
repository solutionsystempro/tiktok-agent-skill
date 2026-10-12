#!/usr/bin/env python3
# Adapted from instagram-agent-skill (c) 2026 Jake Schincariol. Modifications (c) 2026 Ian Ryan Kirk. MIT License.
"""
retention.py - read a TikTok Studio analytics export and find where viewers leave.

Two shapes of file are understood. Columns are found by their header names,
not by position, so extra columns and reordering are fine.

  CURVE    one video's retention: a time column and a retention column.
           Headers such as "Time" / "Second" and "Retention" / "Viewers (%)"
           / "Audience retention". Reports the hook leak (what is lost by
           second 3), the steepest drops, and when the curve crosses 50% and
           25%.

  SUMMARY  one row per video: "Average watch time", "Watched full video"
           (percent), and optionally "Video views", "Duration", "Title".
           Ranks the videos by completion and by average watch time as a
           share of length, against the batch median. A summary has no curve,
           so it cannot show drop-off points; it shows which videos to open.

Whether TikTok Studio offers a given export, and its exact column names, is
unverified and changes between versions. If your file is not recognised, the
error lists the headers it found and the names it looks for, and you can
rename a header to match. Copying the numbers by hand into a two-column CSV
(time, retention %) works too.

The scale of a retention column comes from its header: "%" or "percent" means
percent, "ratio" means 0-1. With neither, the values decide and a note goes to
stderr. --percent or --ratio overrides both.

The thresholds below are this tool's heuristics for flagging, not TikTok
benchmarks. Nothing here is compared against platform averages.

Usage
  python retention.py export.csv
  python retention.py export.csv --json
  python retention.py curve.csv --ratio
"""

import argparse
import csv
import io
import json
import re
import statistics
import sys

HOOK_SECONDS = 3.0       # the window this pack calls the hook
CLIFF_PER_SEC = 2.0      # percentage points lost per second that counts as a cliff
MAX_CLIFFS = 5

ALIASES = {
    "time": ["time", "second", "seconds", "sec", "timestamp", "position",
             "video position", "elapsed", "time (s)", "time (seconds)"],
    "retention": ["retention", "audience retention", "retention rate", "viewers",
                  "viewers (%)", "% of viewers", "viewers remaining", "still watching",
                  "remaining viewers", "audience"],
    "avg_watch": ["average watch time", "avg watch time", "avg. watch time",
                  "average time watched", "avg time watched", "average watch time (s)"],
    "full": ["watched full video", "watched full video (%)", "full video watched",
             "completion rate", "finish rate", "watched full video rate",
             "% watched full video"],
    "views": ["video views", "views", "total views", "plays"],
    "duration": ["duration", "video duration", "video length", "length", "duration (s)"],
    "title": ["title", "video title", "video", "post", "caption", "description",
              "video description"],
}
EXCLUDE = {"views": ["profile"], "time": ["watch time", "play time", "post time",
                                          "create", "date"],
           "title": ["views", "duration", "length", "watch", "id", "link", "url"]}


def norm(h):
    return re.sub(r"\s+", " ", (h or "").replace("﻿", "").strip().lower())


def find_column(headers, field):
    """Exact alias match first, then an alias contained in the header."""
    names = [norm(h) for h in headers]
    excluded = EXCLUDE.get(field, [])
    for alias in ALIASES[field]:
        for i, n in enumerate(names):
            if n == alias:
                return i
    for alias in ALIASES[field]:
        for i, n in enumerate(names):
            if alias in n and not any(x in n for x in excluded):
                return i
    return None


def parse_number(cell):
    s = (cell or "").strip().replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_seconds(cell):
    """'3', '3.5s', '0:03', '00:01:05', '8.3 secs' -> seconds."""
    s = (cell or "").strip().lower()
    if not s:
        return None
    if re.fullmatch(r"\d+(?::\d{1,2}){1,2}(?:\.\d+)?", s):
        total = 0.0
        for part in s.split(":"):
            total = total * 60 + float(part)
        return total
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds)?", s)
    if m:
        return float(m.group(1))
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:m|min|mins|minutes?)", s)
    if m:
        return float(m.group(1)) * 60
    return None


def read_table(text):
    """Returns (headers, rows). The header is the first row that names at
    least one known column, so title lines above it are skipped."""
    text = (text or "").lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise ValueError("the file is empty")
    sample = "\n".join(text.split("\n")[:20])
    delim = max([",", "\t", ";"], key=sample.count)
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delim)
            if any(c.strip() for c in r)]
    for i, r in enumerate(rows):
        if any(find_column(r, f) is not None for f in ("time", "retention", "avg_watch", "full")) \
                and sum(1 for c in r if parse_number(c) is None and c.strip()) >= 2:
            return r, rows[i + 1:]
    return rows[0], rows[1:]


def column_kind(header):
    low = norm(header)
    if "ratio" in low:
        return "ratio"
    if "%" in low or "percent" in low:
        return "percent"
    return None


def scale(values, header, force, notes):
    kind = force or column_kind(header)
    if kind is None:
        kind = "ratio" if values and max(values) <= 1.0 else "percent"
        notes.append(f"scale of \"{header}\" guessed from the values ({kind}); pass "
                     "--ratio or --percent if that is wrong")
    return [v * 100 for v in values] if kind == "ratio" else values


def detect(headers):
    cols = {f: find_column(headers, f) for f in ALIASES}
    if cols["time"] is not None and cols["retention"] is not None:
        return "curve", cols
    if cols["avg_watch"] is not None or cols["full"] is not None:
        return "summary", cols
    found = ", ".join(f"\"{h.strip()}\"" for h in headers if h.strip()) or "none"
    raise ValueError(
        f"could not recognise this export. Headers found: {found}.\n"
        "Need either a retention curve (a time column such as \"Time\" or \"Second\", and a "
        "retention column such as \"Retention\" or \"Viewers (%)\") or a per-video summary "
        "(\"Average watch time\" and/or \"Watched full video\"). Rename a header to one of "
        "these and run it again.")


def hook_point(xs, ys, notes):
    """Retention at exactly HOOK_SECONDS. Interpolated linearly when samples
    sit either side of it. If the curve stops before it, the last observed
    point is used and a note says which second that was. Returns
    (retention, the second it describes)."""
    for x, y in zip(xs, ys):
        if x == HOOK_SECONDS:
            return y, x
    before = [(x, y) for x, y in zip(xs, ys) if x < HOOK_SECONDS]
    after = [(x, y) for x, y in zip(xs, ys) if x > HOOK_SECONDS]
    if before and after:
        (x0, y0), (x1, y1) = before[-1], after[0]
        y = y0 + (y1 - y0) * (HOOK_SECONDS - x0) / (x1 - x0)
        if x1 - x0 > 1:
            notes.append(f"retention at {HOOK_SECONDS:g}s interpolated between samples at "
                         f"{x0:g}s and {x1:g}s")
        return y, HOOK_SECONDS
    if before:
        x, y = before[-1]
        notes.append(f"the curve ends at {x:g}s, before {HOOK_SECONDS:g}s; the hook leak is "
                     f"measured through {x:g}s")
        return y, x
    x, y = after[0]
    notes.append(f"the first sample is at {x:g}s, after {HOOK_SECONDS:g}s; no hook leak can be "
                 "measured")
    return y, x


def analyse_curve(headers, rows, cols, force=None):
    notes, points, skipped = [], [], 0
    for r in rows:
        t = parse_seconds(r[cols["time"]]) if cols["time"] < len(r) else None
        y = parse_number(r[cols["retention"]]) if cols["retention"] < len(r) else None
        if t is None or y is None:
            skipped += 1
            continue
        points.append((t, y))
    if len(points) < 2:
        raise ValueError(f"only {len(points)} usable data point(s) in the retention columns "
                         f"(\"{headers[cols['time']]}\", \"{headers[cols['retention']]}\")")
    if skipped:
        notes.append(f"{skipped} row(s) skipped: not a number in the time or retention column")
    points.sort()
    ys = scale([p[1] for p in points], headers[cols["retention"]], force, notes)
    xs = [p[0] for p in points]
    start = ys[0]
    hook_end, hook_to = hook_point(xs, ys, notes)
    drops = []
    for i in range(1, len(xs)):
        span = (xs[i] - xs[i - 1]) or 1.0
        lost = ys[i - 1] - ys[i]
        drops.append({"from": xs[i - 1], "to": xs[i], "lost": round(lost, 2),
                      "per_second": round(lost / span, 2)})
    cliffs = sorted((d for d in drops if d["per_second"] >= CLIFF_PER_SEC),
                    key=lambda d: -d["per_second"])[:MAX_CLIFFS]

    def crossing(level):
        for x, y in zip(xs, ys):
            if y < level:
                return x
        return None

    return {
        "mode": "curve", "points": len(xs), "start": round(start, 2), "end": round(ys[-1], 2),
        "length_seconds": xs[-1],
        "hook_leak": round(start - hook_end, 2), "hook_window": HOOK_SECONDS,
        "hook_measured_to": round(hook_to, 2),
        "cliffs": sorted(cliffs, key=lambda d: d["from"]),
        "below_50_at": crossing(50.0), "below_25_at": crossing(25.0),
        "thresholds": {"hook_seconds": HOOK_SECONDS, "cliff_points_per_second": CLIFF_PER_SEC},
        "notes": notes,
    }


def analyse_summary(headers, rows, cols, force=None):
    notes, videos, skipped = [], [], 0

    def cell(r, field):
        i = cols.get(field)
        return r[i] if i is not None and i < len(r) else ""

    for n, r in enumerate(rows, 1):
        avg = parse_seconds(cell(r, "avg_watch")) if cols["avg_watch"] is not None else None
        full = parse_number(cell(r, "full")) if cols["full"] is not None else None
        if avg is None and full is None:
            skipped += 1
            continue
        videos.append({
            "title": cell(r, "title").strip() or f"row {n}",
            "views": parse_number(cell(r, "views")),
            "avg_watch": avg, "full": full,
            "duration": parse_seconds(cell(r, "duration")),
        })
    if not videos:
        raise ValueError("no rows with a readable average watch time or watched-full-video value")
    if skipped:
        notes.append(f"{skipped} row(s) skipped: no readable watch time or completion value")
    if cols["full"] is not None:
        fulls = [v["full"] for v in videos if v["full"] is not None]
        scaled = scale(fulls, headers[cols["full"]], force, notes)
        it = iter(scaled)
        for v in videos:
            if v["full"] is not None:
                v["full"] = round(next(it), 2)
    for v in videos:
        v["watch_share"] = (round(v["avg_watch"] / v["duration"] * 100, 1)
                            if v["avg_watch"] is not None and v["duration"] else None)
    key = "full" if any(v["full"] is not None for v in videos) else \
        ("watch_share" if any(v["watch_share"] is not None for v in videos) else "avg_watch")
    vals = [v[key] for v in videos if v[key] is not None]
    med = statistics.median(vals) if vals else None
    for v in videos:
        v["vs_median"] = (round(v[key] - med, 2) if v[key] is not None and med is not None
                          else None)
    ranked = sorted(videos, key=lambda v: -(v[key] if v[key] is not None else -1e9))
    if cols["duration"] is None:
        notes.append("no duration column, so average watch time cannot be shown as a share "
                     "of length")
    notes.append("a per-video summary has no retention curve. Open the bottom videos in "
                 "TikTok Studio to see where viewers left")
    return {"mode": "summary", "videos": ranked, "ranked_by": key,
            "median": round(med, 2) if med is not None else None, "notes": notes}


def analyse_text(text, force=None):
    headers, rows = read_table(text)
    mode, cols = detect(headers)
    if mode == "curve":
        return analyse_curve(headers, rows, cols, force)
    return analyse_summary(headers, rows, cols, force)


def fmt_s(x):
    return "-" if x is None else f"{x:.1f}s"


def render(a, out=sys.stdout):
    if a["mode"] == "curve":
        print(f"\nRETENTION CURVE  ·  {a['points']} points  ·  {a['start']:.1f}% -> "
              f"{a['end']:.1f}% over {a['length_seconds']:.0f}s", file=out)
        print("=" * 70, file=out)
        print(f"  HOOK LEAK   {a['hook_leak']:.1f} points lost by second "
              f"{a['hook_measured_to']:g}"
              + ("" if a["hook_measured_to"] == a["hook_window"]
                 else f" (curve does not reach {a['hook_window']:g}s)"), file=out)
        print("  CLIFFS      steepest drops "
              f"(>= {a['thresholds']['cliff_points_per_second']} points per second)", file=out)
        for c in a["cliffs"]:
            print(f"    {c['from']:6.1f}s -> {c['to']:6.1f}s   -{c['lost']:.1f} points "
                  f"({c['per_second']:.1f}/s)", file=out)
        if not a["cliffs"]:
            print("    none. The loss is a steady slide, not a moment", file=out)
        print(f"  BELOW 50%   {fmt_s(a['below_50_at'])}", file=out)
        print(f"  BELOW 25%   {fmt_s(a['below_25_at'])}", file=out)
    else:
        label = {"full": "watched full video %", "watch_share": "avg watch as % of length",
                 "avg_watch": "average watch time (s)"}[a["ranked_by"]]
        print(f"\nRETENTION SUMMARY  ·  {len(a['videos'])} videos  ·  ranked by {label}  ·  "
              f"median {a['median']}", file=out)
        print("=" * 78, file=out)
        for v in a["videos"]:
            val = v[a["ranked_by"]]
            delta = f"{v['vs_median']:+.1f}" if v["vs_median"] is not None else "   -"
            print(f"  {('-' if val is None else val):>7}  {delta:>7}  avg {fmt_s(v['avg_watch']):>7}"
                  f"  {v['title'][:44]}", file=out)
    print("-" * 70, file=out)
    for n in a["notes"]:
        print(f"  note: {n}", file=out)
    print("  Thresholds are this tool's heuristics, not TikTok benchmarks.\n", file=out)


def main():
    ap = argparse.ArgumentParser(description="Find drop-off in a TikTok Studio export.")
    ap.add_argument("input", help="CSV export, or - for stdin")
    ap.add_argument("--json", action="store_true")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--ratio", action="store_true", help="retention values are 0-1")
    g.add_argument("--percent", action="store_true", help="retention values are 0-100")
    args = ap.parse_args()

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):   # Windows pipes default to cp1252
            stream.reconfigure(encoding="utf-8", errors="replace")
    force = "ratio" if args.ratio else ("percent" if args.percent else None)
    try:
        if args.input == "-":
            text = sys.stdin.read()
        else:
            with open(args.input, encoding="utf-8-sig", newline="") as fh:
                text = fh.read()
        a = analyse_text(text, force)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
    if args.json:
        print(json.dumps(a, indent=2, ensure_ascii=False))
    else:
        render(a)


if __name__ == "__main__":
    main()
