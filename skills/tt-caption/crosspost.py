#!/usr/bin/env python3
# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
"""
crosspost.py - check one video's cross-post pack against each platform's
limits: a TikTok caption, a YouTube Shorts title and description, and an
Instagram Reels caption.

Input is one file with a section per platform. Section headers are lines in
square brackets; any you leave out are reported as missing:

    [tiktok]
    Sourdough starter in 5 days...
    [shorts title]
    Sourdough starter in 5 days, no fancy flour
    [shorts description]
    Day 1 is flour and water...
    [reels]
    Sourdough starter in 5 days...

Limits and where they come from:

  TikTok caption        2,200 UTF-16 units. Verified: Content Posting API
                        https://developers.tiktok.com/doc/content-posting-api-reference-direct-post/
  Shorts title          100 characters, no < or >. Verified: YouTube Data API
                        https://developers.google.com/youtube/v3/docs/videos
  Shorts description    5,000 bytes (UTF-8), no < or >. Verified: same page.
  Reels caption         2,200 characters and up to 5 hashtags, as used by the
                        instagram-agent-skill caption linter. Not re-verified
                        for this pack: UNVERIFIED here.
  Reels preview         about 125 characters before "more". Approximation.

Usage
  python crosspost.py pack.txt
  python crosspost.py pack.txt --json
"""

import argparse
import json
import re
import sys

TIKTOK_UNITS = 2200
SHORTS_TITLE_CHARS = 100
SHORTS_DESC_BYTES = 5000
REELS_CHARS = 2200
REELS_HASHTAGS = 5
REELS_PREVIEW = 125

SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
SECTION_NAMES = {
    "tiktok": "tiktok", "tiktok caption": "tiktok",
    "shorts title": "shorts_title", "youtube title": "shorts_title", "title": "shorts_title",
    "shorts description": "shorts_description", "youtube description": "shorts_description",
    "description": "shorts_description",
    "reels": "reels", "reels caption": "reels", "instagram": "reels",
    "instagram caption": "reels",
}
LABELS = {"tiktok": "TikTok caption", "shorts_title": "Shorts title",
          "shorts_description": "Shorts description", "reels": "Reels caption"}
HASHTAG_RE = re.compile(r"(?:^|(?<=\s))(#\w+)")
OTHER_PLATFORM = {
    "tiktok": re.compile(r"(?i)\b(?:youtube|subscribe|reels?|instagram|link in (?:my )?description)\b"),
    "shorts_title": re.compile(r"(?i)\b(?:tiktok|reels?|instagram|fyp)\b"),
    "shorts_description": re.compile(r"(?i)\b(?:tiktok|reels?|instagram|#fyp)\b"),
    "reels": re.compile(r"(?i)\b(?:tiktok|youtube|subscribe|#fyp|#foryou)\b"),
}


def parse(text):
    text = (text or "").lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    sections, current, unknown = {}, None, []
    for line in text.split("\n"):
        m = SECTION_RE.match(line)
        if m:
            name = m.group(1).strip().lower()
            current = SECTION_NAMES.get(name)
            if current is None:
                unknown.append(m.group(1).strip())
            else:
                sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}, unknown


def check(sections):
    results = {}

    def add(key, status, detail):
        results.setdefault(key, []).append({"status": status, "detail": detail})

    for key in LABELS:
        text = sections.get(key)
        if text is None:
            add(key, "FAIL", "section missing")
            continue
        if not text:
            add(key, "FAIL", "section is empty")
            continue
        if OTHER_PLATFORM[key].search(text):
            add(key, "WARN", f"mentions another platform (\"{OTHER_PLATFORM[key].search(text).group(0)}\")")

    t = sections.get("tiktok")
    if t:
        units = len(t.encode("utf-16-le")) // 2
        add("tiktok", "FAIL" if units > TIKTOK_UNITS else "PASS",
            f"{units} / {TIKTOK_UNITS} UTF-16 units (verified API limit)")

    st = sections.get("shorts_title")
    if st:
        n = len(st)
        add("shorts_title", "FAIL" if n > SHORTS_TITLE_CHARS else "PASS",
            f"{n} / {SHORTS_TITLE_CHARS} characters (verified API limit)")
        if "\n" in st:
            add("shorts_title", "WARN", "title has a line break")
    sd = sections.get("shorts_description")
    if sd:
        b = len(sd.encode("utf-8"))
        add("shorts_description", "FAIL" if b > SHORTS_DESC_BYTES else "PASS",
            f"{b} / {SHORTS_DESC_BYTES} bytes (verified API limit; emoji and accents take "
            "more than one byte)")
    for key in ("shorts_title", "shorts_description"):
        if sections.get(key) and re.search(r"[<>]", sections[key]):
            add(key, "FAIL", "contains < or >, which the YouTube Data API does not allow")

    r = sections.get("reels")
    if r:
        n = len(r)
        add("reels", "FAIL" if n > REELS_CHARS else "PASS",
            f"{n} / {REELS_CHARS} characters (instagram-agent-skill limit, unverified here)")
        tags = HASHTAG_RE.findall(r)
        add("reels", "FAIL" if len(tags) > REELS_HASHTAGS else "PASS",
            f"{len(tags)} / {REELS_HASHTAGS} hashtags (instagram-agent-skill limit, unverified here)")
        first = r.split("\n", 1)[0]
        add("reels", "WARN" if len(first) > REELS_PREVIEW else "PASS",
            f"first line {len(first)} characters, preview cut about {REELS_PREVIEW} (approximation)")

    statuses = [c["status"] for v in results.values() for c in v]
    verdict = "FIX" if "FAIL" in statuses else ("REVIEW" if "WARN" in statuses else "READY")
    return {"platforms": results, "verdict": verdict}


def render(r, unknown, out=sys.stdout):
    print("\nCROSS-POST PACK", file=out)
    print("=" * 72, file=out)
    for key, label in LABELS.items():
        print(f"  {label}", file=out)
        for c in r["platforms"].get(key, []):
            print(f"    {c['status']:<5} {c['detail']}", file=out)
    for u in unknown:
        print(f"  note: unknown section [{u}] ignored", file=out)
    print("-" * 72, file=out)
    print(f"  VERDICT  {r['verdict']}\n", file=out)


def main():
    ap = argparse.ArgumentParser(description="Check a cross-post pack against platform limits.")
    ap.add_argument("input", nargs="?", default="-", help="pack file, or - for stdin")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):   # Windows pipes default to cp1252
            stream.reconfigure(encoding="utf-8", errors="replace")
    if args.input == "-":
        text = sys.stdin.read()
    else:
        with open(args.input, encoding="utf-8-sig") as fh:
            text = fh.read()
    sections, unknown = parse(text)
    if not sections:
        print("no sections found. Use [tiktok], [shorts title], [shorts description] and "
              "[reels] headers.", file=sys.stderr)
        sys.exit(2)
    r = check(sections)
    if args.json:
        print(json.dumps(dict(r, unknown_sections=unknown), indent=2, ensure_ascii=False))
    else:
        render(r, unknown)
    sys.exit(0 if r["verdict"] == "READY" else 1)


if __name__ == "__main__":
    main()
