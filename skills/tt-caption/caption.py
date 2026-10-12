#!/usr/bin/env python3
# Adapted from instagram-agent-skill (c) 2026 Jake Schincariol. Modifications (c) 2026 Ian Ryan Kirk. MIT License.
"""
caption.py - lint a TikTok caption and its on-screen text before you post.

What it checks
  LENGTH          2,200 counted in UTF-16 code units. That is the limit on the
                  `title` field of TikTok's Content Posting API ("The maximum
                  length is 2200 in UTF-16 runes"):
                  https://developers.tiktok.com/doc/content-posting-api-reference-direct-post/
                  Most emoji are two UTF-16 units, so a caption that looks like
                  2,150 characters can be over. The in-app limit may differ;
                  that is unverified, so this tool uses the documented one.
  FIRST LINE      a preview of what shows before the caption is cut off. The
                  cut point is an approximation (default 90 characters) and is
                  unverified: it moves with the device, the font and the
                  length of the video's on-screen elements.
  HASHTAGS        count and placement. The count guidance (up to 5) is a
                  HEURISTIC from this pack, not a TikTok rule. TikTok does not
                  publish a hashtag cap that we could verify.
  SEARCH TERMS    whether the phrases you want to be found for are in the
                  caption, in the visible window, and in the on-screen text.
  EMOJI           counted as graphemes (a skin tone or a ZWJ family is one),
                  with density reported.
  ON-SCREEN       with --onscreen FILE: one card per line, word count per card.

Usage
  python caption.py caption.txt
  python caption.py caption.txt --keywords "sourdough starter,bread recipe"
  python caption.py caption.txt --onscreen cards.txt --keywords "sourdough"
  type caption.txt | python caption.py -
  python caption.py caption.txt --json
"""

import argparse
import json
import re
import sys
import textwrap

LIMIT = 2200             # UTF-16 units, Content Posting API `title` field.
TRUNCATE = 90            # Approximate visible caption before "more". Unverified.
HASHTAG_GUIDE = 5        # Heuristic, not a TikTok rule.
CARD_WORDS = 8           # Heuristic: words per on-screen card.

HASHTAG_RE = re.compile(r"(?:^|(?<=\s))(#\w+)")   # \w is Unicode-aware: #café counts
MENTION_RE = re.compile(r"(?:^|(?<=\s))(@[A-Za-z0-9_.]+)")
LINK_RE = re.compile(r"https?://\S+|\bwww\.\S+", re.IGNORECASE)
WORD_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)?")
CONCRETE_RE = re.compile(r"\$\s?\d|\b\d[\d,.]*\b|(?<![.!?]\s)(?<!^)\b[A-Z][a-z]{2,}\b", re.MULTILINE)

# One emoji grapheme: a pictographic base, optional variation selector and
# skin tone, optionally joined to more of the same by U+200D. Regional
# indicator pairs (flags) count as one.
_PICT = "[\U0001F300-\U0001FAFF☀-➿←-⇿⬀-⯿⌀-⏿]"
_MOD = "[️\U0001F3FB-\U0001F3FF]*"
EMOJI_RE = re.compile(
    "(?:[\U0001F1E6-\U0001F1FF]{2})|(?:" + _PICT + _MOD + "(?:‍" + _PICT + _MOD + ")*)")

ASKS = [
    (re.compile(r"(?i)\bcomment (?:the word |\")?[A-Z0-9]{2,}\b"), "comment a keyword"),
    (re.compile(r"(?i)\bsave (?:this|it)\b"), "save this"),
    (re.compile(r"(?i)\bshare (?:this|it)\b|\bsend (?:this|it) to\b"), "share this"),
    (re.compile(r"(?i)\bfollow (?:me|for)\b"), "follow"),
    (re.compile(r"(?i)\blink in (?:my )?bio\b"), "link in bio"),
    (re.compile(r"(?i)\b(?:stitch|duet) (?:this|me)\b"), "stitch or duet"),
    (re.compile(r"(?i)\bpart (?:2|two)\b"), "part 2"),
    (re.compile(r"(?i)\btell me\b|\bwhat would you\b|\bwhich one\b|\bdrop (?:your|a)\b"),
     "answer a question"),
]

FILLER_TAGS = {"#fyp", "#foryou", "#foryoupage", "#fypシ", "#viral", "#trending",
               "#xyzbca", "#tiktok", "#explore", "#blowthisup", "#goviral", "#fy"}


def utf16_len(text):
    return len(text.encode("utf-16-le")) // 2


def visible_window(text, cut):
    """The first line, cut at `cut` characters. TikTok also cuts at the first
    line break in many layouts, so the window never runs past it."""
    first = text.strip().split("\n", 1)[0]
    return first if len(first) <= cut else first[:cut]


def render_box(window, truncated, out=sys.stdout, width=52):
    print("\n  WHAT THE PREVIEW SHOWS (approximate)", file=out)
    print("  +" + "-" * (width + 2) + "+", file=out)
    for line in (textwrap.wrap(window, width) or [""])[:4]:
        print(f"  | {line:<{width}} |", file=out)
    tail = "... more" if truncated else "(whole caption fits)"
    print("  +" + "-" * (width + 2 - len(tail) - 2) + f" {tail} " + "+", file=out)


def analyse(text, cut=TRUNCATE, keywords=None, onscreen=None):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿").rstrip()
    stripped = text.strip()
    points = len(stripped)
    units = utf16_len(stripped)
    # Taken from the raw text, before strip(), so a caption that opens on a
    # blank line is caught rather than silently tidied.
    first_line = text.split("\n", 1)[0].strip() if stripped else ""
    tags = HASHTAG_RE.findall(stripped)
    mentions = MENTION_RE.findall(stripped)
    links = LINK_RE.findall(stripped)
    emoji = EMOJI_RE.findall(stripped)
    window = visible_window(stripped, cut)
    truncated = stripped != window
    asks = [name for pattern, name in ASKS if pattern.search(stripped)]
    filler = [t for t in tags if t.lower() in FILLER_TAGS]
    keywords = [k.strip() for k in (keywords or []) if k.strip()]
    cards = [l.strip() for l in (onscreen or "").replace("\r\n", "\n").lstrip("﻿")
             .split("\n") if l.strip()]

    checks = []

    def add(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})

    if units > LIMIT:
        add("LENGTH", "FAIL", f"{units} / {LIMIT} UTF-16 units, {units - LIMIT} over"
            + (f" ({points} characters; emoji count double)" if units != points else ""))
    elif units > LIMIT * 0.95:
        add("LENGTH", "WARN", f"{units} / {LIMIT} UTF-16 units, close to the limit")
    else:
        add("LENGTH", "PASS", f"{units} / {LIMIT} UTF-16 units"
            + (f" ({points} characters)" if units != points else ""))

    if not stripped:
        add("FIRST LINE", "FAIL", "the caption is empty")
    elif not first_line:
        add("FIRST LINE", "FAIL", "the caption opens on a blank line")
    elif first_line.startswith("#") or first_line.startswith("@"):
        add("FIRST LINE", "FAIL", "opens on a hashtag or mention, the most visible spot spent "
                                  "on a label")
    elif len(first_line) > cut:
        add("FIRST LINE", "WARN", f"{len(first_line)} characters, likely cut near {cut}. "
                                  "Fine if the cut lands on a cliffhanger")
    else:
        add("FIRST LINE", "PASS", f"{len(first_line)} characters, likely shows whole")

    if stripped:
        hits = CONCRETE_RE.findall(window)
        add("CONCRETE", "PASS" if hits else "WARN",
            f"{len(hits)} number(s) or name(s) in the visible window"
            + ("" if hits else ", nothing specific before the cut"))

    label = f"(heuristic, not a TikTok rule: up to {HASHTAG_GUIDE})"
    if len(tags) > HASHTAG_GUIDE:
        add("HASHTAGS", "WARN", f"{len(tags)} tags {label}. A wall of tags reads as spam "
                                "and pushes the words people search out of view")
    elif filler:
        add("HASHTAGS", "WARN", f"{len(tags)} tags, {len(filler)} generic "
                                f"({', '.join(filler[:3])}). They describe nothing about "
                                f"the video {label}")
    else:
        add("HASHTAGS", "PASS", f"{len(tags)} tag(s) {label}"
            + (f": {' '.join(tags)}" if tags else ""))

    if tags:
        in_window = [t for t in tags if t in HASHTAG_RE.findall(window)]
        if in_window and window.lstrip().startswith("#"):
            add("TAG PLACEMENT", "WARN", "the caption leads with a hashtag")
        elif in_window and len(in_window) > 1:
            add("TAG PLACEMENT", "WARN", f"{len(in_window)} hashtags inside the visible window, "
                                         "spending it on labels")
        else:
            add("TAG PLACEMENT", "PASS", "tags sit after the words")

    if links:
        add("LINKS", "WARN", f"{len(links)} link(s). Links in TikTok captions are generally "
                             "not clickable (unverified for every account type). Use the bio")

    if stripped:
        if len(asks) == 1:
            add("ONE ASK", "PASS", f"one call to action: {asks[0]}")
        elif not asks:
            add("ONE ASK", "WARN", "no call to action. Decide what this video is for")
        else:
            add("ONE ASK", "WARN", f"{len(asks)} asks ({', '.join(asks)}). Pick one")

    if emoji:
        density = len(emoji) * 100 / max(points, 1)
        status = "WARN" if density > 4 else "PASS"
        add("EMOJI", status, f"{len(emoji)} emoji, {density:.1f} per 100 characters"
            + (", reads as decoration" if status == "WARN" else ""))
        if EMOJI_RE.match(stripped):
            add("EMOJI LEAD", "WARN", "the caption opens on an emoji, which pushes the first "
                                      "word further into the cut")

    if keywords:
        low = stripped.lower()
        low_window = window.lower()
        low_cards = " ".join(cards).lower()
        found = [k for k in keywords if k.lower() in low]
        missing = [k for k in keywords if k.lower() not in low]
        early = [k for k in found if k.lower() in low_window]
        status = "PASS" if not missing else ("WARN" if found else "FAIL")
        add("SEARCH TERMS", status,
            f"{len(found)}/{len(keywords)} in the caption, {len(early)} in the visible window"
            + (f". Missing: {', '.join(missing)}" if missing else ""))
        if cards:
            on = [k for k in keywords if k.lower() in low_cards]
            add("SEARCH ON SCREEN", "PASS" if on else "WARN",
                f"{len(on)}/{len(keywords)} also in the on-screen text")

    for i, card in enumerate(cards, 1):
        n = len(WORD_RE.findall(card))
        if n > CARD_WORDS:
            add(f"CARD {i}", "WARN", f"{n} words on one card (heuristic: {CARD_WORDS} or "
                                     "fewer reads at a glance)")
        elif HASHTAG_RE.search(card):
            add(f"CARD {i}", "WARN", "a hashtag on screen reads as a label")
        else:
            add(f"CARD {i}", "PASS", f"{n} words")

    fails = sum(1 for c in checks if c["status"] == "FAIL")
    warns = sum(1 for c in checks if c["status"] == "WARN")
    verdict = "FIX" if fails else ("REVIEW" if warns else "READY")
    return {
        "characters": points, "utf16_units": units, "limit": LIMIT, "truncate_at": cut,
        "visible": window, "truncated": truncated, "first_line_chars": len(first_line),
        "hashtags": tags, "mentions": mentions, "links": links, "emoji": len(emoji),
        "asks": asks, "cards": len(cards), "checks": checks, "verdict": verdict,
    }


def render(a, out=sys.stdout):
    head = (f"TIKTOK CAPTION LINT  ·  {a['utf16_units']} / {a['limit']} UTF-16 units  ·  "
            f"{len(a['hashtags'])} hashtags")
    print("\n" + head, file=out)
    print("=" * max(len(head), 62), file=out)
    render_box(a["visible"], a["truncated"], out=out)
    print("", file=out)
    for c in a["checks"]:
        print(f"  {c['status']:<5} {c['check']:<17} {c['detail']}", file=out)
    print("-" * max(len(head), 62), file=out)
    print(f"  VERDICT  {a['verdict']}\n", file=out)


def read(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def main():
    ap = argparse.ArgumentParser(description="Lint a TikTok caption.")
    ap.add_argument("input", nargs="?", default="-", help="caption file, or - for stdin")
    ap.add_argument("--truncate", type=int, default=TRUNCATE,
                    help=f"approximate characters shown before the cut (default {TRUNCATE})")
    ap.add_argument("--keywords", default="", help="comma-separated search terms")
    ap.add_argument("--onscreen", help="file with on-screen text, one card per line")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.truncate < 1:
        ap.error("--truncate must be at least 1")

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):   # Windows pipes default to cp1252
            stream.reconfigure(encoding="utf-8", errors="replace")
    a = analyse(read(args.input), cut=args.truncate, keywords=args.keywords.split(","),
                onscreen=read(args.onscreen) if args.onscreen else None)
    if args.json:
        print(json.dumps(a, indent=2, ensure_ascii=False))
    else:
        render(a)
    sys.exit(0 if a["verdict"] == "READY" else 1)


if __name__ == "__main__":
    main()
