#!/usr/bin/env python3
# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
"""
kwmap.py - turn search phrases you pasted into a TikTok keyword map.

Input is whatever you copied by hand: the suggestions TikTok search shows as
you type, the "Others searched for" list, a keyword list from TikTok Creative
Center, related searches under a video. One phrase per line. Lines starting
with "# " mark where each list came from, so a phrase that shows up in
several places counts for more:

    # search suggestions: sourdough
    sourdough starter
    sourdough starter for beginners
    # others searched for
    sourdough discard recipes

A CSV or TSV with a header works too: the column named "keyword" (or "term",
"query", "search term") is the phrase, and a column named like "popularity",
"volume", "posts" or "views" is kept as a relative number.

This tool does not fetch anything. Every phrase comes from you.

Output: the primary keyword, secondary keywords, long-tail phrases and
questions, each with where it goes (spoken in the hook, on screen, caption
line one, caption body, hashtag).

Usage
  python kwmap.py pasted.txt --seed "sourdough"
  python kwmap.py creative_center.csv --json
"""

import argparse
import csv
import io
import json
import re
import sys

STOP = {"the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "my",
        "your", "is", "how", "what", "why", "best", "vs", "at", "it", "i", "you", "do"}
QUESTION_RE = re.compile(r"(?i)^(?:how|why|what|when|where|which|who|can|does|do|is|are|should)\b")
KW_COLUMNS = ("keyword", "keywords", "term", "query", "search term", "search_term", "phrase")
VOL_COLUMNS = ("popularity", "volume", "posts", "views", "search volume", "impressions",
               "score")


def clean(phrase):
    p = (phrase or "").replace("﻿", "").strip().lower()
    p = re.sub(r"^(?:[#\-\*\u2022]+\s*|\d+[.)]\s+)+", "", p)    # bullets, "1. ", leading #
    # Trailing counts copied with the phrase: "12.5k posts", "3M views", "40K".
    p = re.sub(r"\s+\d[\d.,]*\s*[kmb]?\s*(?:posts|views|videos)$|\s+\d[\d.,]*[kmb]$", "", p)
    p = re.sub(r"\s+", " ", p).strip(" \t\"'.,;:")
    return p


def parse_number(cell):
    s = (cell or "").strip().lower().replace(",", "")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([kmb]?)", s)
    if not m:
        return None
    return float(m.group(1)) * {"": 1, "k": 1e3, "m": 1e6, "b": 1e9}[m.group(2)]


def read(text):
    """Returns a list of (phrase, source, volume)."""
    text = (text or "").lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    lines = [l for l in text.split("\n") if l.strip()]
    if not lines:
        return []
    head = lines[0]
    delim = "\t" if "\t" in head else ("," if "," in head else None)
    if delim:
        cells = [c.strip().lower() for c in next(csv.reader([head], delimiter=delim))]
        kw = next((i for i, c in enumerate(cells) if c in KW_COLUMNS), None)
        if kw is not None:
            vol = next((i for i, c in enumerate(cells) if any(v in c for v in VOL_COLUMNS)), None)
            out = []
            for r in csv.reader(io.StringIO("\n".join(lines[1:])), delimiter=delim):
                if kw < len(r) and clean(r[kw]):
                    v = parse_number(r[vol]) if vol is not None and vol < len(r) else None
                    out.append((clean(r[kw]), "table", v))
            return out
    out, source = [], "pasted"
    for line in lines:
        s = line.strip()
        if s.startswith("# ") or s.startswith("##"):
            source = s.lstrip("#").strip().lower() or "pasted"
            continue
        p = clean(s)
        if p:
            out.append((p, source, None))
    return out


def content_words(phrase):
    return [w for w in re.findall(r"[^\W_]+", phrase) if w not in STOP]


def build(entries, seed=None):
    phrases = {}
    for p, src, vol in entries:
        e = phrases.setdefault(p, {"phrase": p, "sources": set(), "mentions": 0, "volume": None})
        e["sources"].add(src)
        e["mentions"] += 1
        if vol is not None:
            e["volume"] = max(vol, e["volume"] or 0)
    if not phrases:
        return None
    seed = clean(seed) if seed else None
    # How many other phrases contain each phrase: a head term sits inside many.
    for e in phrases.values():
        e["contained_in"] = sum(1 for o in phrases if o != e["phrase"]
                                and re.search(r"\b" + re.escape(e["phrase"]) + r"\b", o))
        e["words"] = len(e["phrase"].split())
        e["question"] = bool(QUESTION_RE.match(e["phrase"]))
        e["has_seed"] = bool(seed and seed in e["phrase"])
        e["score"] = (len(e["sources"]) * 3 + e["mentions"] + e["contained_in"] * 2
                      + (2 if e["has_seed"] else 0) - max(0, e["words"] - 3))
    # A pasted volume column outranks the mention score when there is one.
    ranked = sorted(phrases.values(), key=lambda e: (-(e["volume"] or 0), -e["score"],
                                                     e["words"], e["phrase"]))
    non_q = [e for e in ranked if not e["question"]]
    primary = (non_q or ranked)[0]
    rest = [e for e in ranked if e is not primary]
    questions = [e for e in rest if e["question"]]
    long_tail = [e for e in rest if not e["question"] and e["words"] >= 4]
    secondary = [e for e in rest if not e["question"] and e["words"] < 4][:5]
    extra = [e for e in rest if not e["question"] and e["words"] < 4][5:]
    tags = []
    for e in [primary] + secondary:
        tag = "#" + re.sub(r"[^\w]", "", e["phrase"])
        if len(tag) > 1 and tag not in tags:
            tags.append(tag)

    def out(e):
        return {"phrase": e["phrase"], "sources": sorted(e["sources"]),
                "mentions": e["mentions"], "volume": e["volume"], "score": e["score"]}

    return {
        "phrases": len(phrases),
        "primary": out(primary),
        "secondary": [out(e) for e in secondary],
        "long_tail": [out(e) for e in long_tail],
        "questions": [out(e) for e in questions],
        "other": [out(e) for e in extra],
        "hashtags": tags[:4],
        "placement": {
            "spoken_hook": primary["phrase"],
            "on_screen": primary["phrase"],
            "caption_first_line": primary["phrase"],
            "caption_body": [e["phrase"] for e in secondary[:2]],
            "video_ideas": [e["phrase"] for e in questions[:3] + long_tail[:2]],
        },
    }


def render(m, out=sys.stdout):
    print(f"\nKEYWORD MAP  ·  {m['phrases']} unique phrases", file=out)
    print("=" * 66, file=out)
    p = m["primary"]
    print(f"  PRIMARY     {p['phrase']}   ({len(p['sources'])} source(s), "
          f"{p['mentions']} mention(s))", file=out)
    for title, key in (("SECONDARY", "secondary"), ("LONG TAIL", "long_tail"),
                       ("QUESTIONS", "questions")):
        items = m[key]
        print(f"  {title:<11} " + ("; ".join(e["phrase"] for e in items[:6]) or "-"), file=out)
    print(f"  HASHTAGS    {' '.join(m['hashtags'])}   (pick a few, heuristic)", file=out)
    print("-" * 66, file=out)
    pl = m["placement"]
    print(f"  say it in the hook:     \"{pl['spoken_hook']}\"", file=out)
    print(f"  put it on screen:       \"{pl['on_screen']}\"", file=out)
    print(f"  caption line one:       \"{pl['caption_first_line']}\"", file=out)
    print(f"  caption body:           {', '.join(pl['caption_body']) or '-'}", file=out)
    print(f"  separate videos:        {'; '.join(pl['video_ideas']) or '-'}", file=out)
    print("\n  Ranked from what you pasted, not from TikTok data. A phrase seen in more "
          "lists ranks higher.\n", file=out)


def main():
    ap = argparse.ArgumentParser(description="Build a TikTok keyword map from pasted phrases.")
    ap.add_argument("input", nargs="?", default="-", help="text or CSV file, or - for stdin")
    ap.add_argument("--seed", help="the topic you searched for")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):   # Windows pipes default to cp1252
            stream.reconfigure(encoding="utf-8", errors="replace")
    if args.input == "-":
        text = sys.stdin.read()
    else:
        with open(args.input, encoding="utf-8-sig", newline="") as fh:
            text = fh.read()
    m = build(read(text), args.seed)
    if not m:
        print("no phrases found. Paste one search phrase per line.", file=sys.stderr)
        sys.exit(2)
    if args.json:
        print(json.dumps(m, indent=2, ensure_ascii=False))
    else:
        render(m)


if __name__ == "__main__":
    main()
