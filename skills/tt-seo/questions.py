#!/usr/bin/env python3
# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
"""
questions.py - cluster the questions people ask about a topic and turn each
cluster into script ideas.

Input is questions you collected by hand, one per line: TikTok search
suggestions that are questions, "People also ask" boxes in web search, Q&A
sites, forum threads, the comments under your own videos. Lines starting with
"# " name the source. This tool fetches nothing.

    # tiktok search suggestions
    how to keep sourdough starter alive
    why is my sourdough starter not rising
    # people also ask
    How often do you feed a sourdough starter?

Clustering is simple and explainable: each question joins the cluster of its
most widely shared topic word (a word, not a stop word, that appears in at
least two questions and is not one of your --seed words). Questions with no
shared word go to "other". Near-duplicates (same words after normalising) are
merged and counted.

Each cluster becomes script ideas: one video per question (hook formula #5,
The Typed Question), and for clusters of three or more, one round-up video
(formula #6, Numbered Lessons).

Usage
  python questions.py questions.txt --seed "sourdough,starter"
  python questions.py questions.txt --json
"""

import argparse
import json
import re
import sys

STOP = {
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "for", "with", "at",
    "by", "from", "is", "are", "was", "were", "be", "been", "do", "does", "did", "can",
    "could", "should", "would", "will", "i", "you", "my", "your", "me", "we", "it", "its",
    "this", "that", "these", "those", "how", "what", "why", "when", "where", "which", "who",
    "whom", "much", "many", "long", "often", "get", "make", "use", "have", "has", "if",
    "so", "not", "no", "yes", "too", "very", "best", "good", "way", "ways", "there", "than",
    "vs", "versus", "need", "want", "into", "about", "after", "before", "without", "out",
    "up", "off", "any", "all", "one", "still", "keep",
}


def clean(line):
    q = (line or "").replace("\ufeff", "").strip()
    q = re.sub(r"^(?:[\-\*\u2022>]+\s*|\d+[.)]\s+|q:\s*)+", "", q, flags=re.IGNORECASE)
    q = re.sub(r"\s+", " ", q).strip(" \t\"'")
    return q


def words(q):
    return [w for w in re.findall(r"[^\W_]+(?:'[^\W_]+)?", q.lower())]


def stem(w):
    """Light plural folding so 'starters' and 'starter' meet. Not a real stemmer."""
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def read(text):
    """Returns a list of (question, source)."""
    text = (text or "").lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    out, source = [], "pasted"
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.startswith("# ") or s.startswith("##"):
            source = s.lstrip("#").strip().lower() or "pasted"
            continue
        q = clean(s)
        if q:
            out.append((q, source))
    return out


def cluster(entries, seed=None):
    seeds = {stem(w) for s in (seed or []) for w in words(s)}
    merged = {}
    for q, src in entries:
        key = " ".join(stem(w) for w in words(q) if w not in STOP)
        if not key:
            key = q.lower()
        e = merged.setdefault(key, {"question": q if q.endswith("?") else q + "?",
                                    "sources": set(), "count": 0,
                                    "terms": {stem(w) for w in words(q) if w not in STOP}})
        e["sources"].add(src)
        e["count"] += 1
    if not merged:
        return None
    qs = list(merged.values())
    df = {}
    for e in qs:
        for t in e["terms"] - seeds:
            df[t] = df.get(t, 0) + 1
    clusters = {}
    for e in qs:
        shared = [t for t in e["terms"] - seeds if df.get(t, 0) >= 2 and len(t) >= 3]
        topic = sorted(shared, key=lambda t: (-df[t], t))[0] if shared else "other"
        clusters.setdefault(topic, []).append(e)
    result = []
    for topic, items in clusters.items():
        items.sort(key=lambda e: (-len(e["sources"]), -e["count"], e["question"].lower()))
        ideas = [{"formula": "#5 The Typed Question", "question": e["question"],
                  "spoken_hook": e["question"][0].upper() + e["question"][1:],
                  "on_screen": e["question"].rstrip("?").upper()[:40]}
                 for e in items]
        if len(items) >= 3 and topic != "other":
            ideas.insert(0, {"formula": "#6 Numbered Lessons",
                             "question": f"{len(items)} questions about {topic}",
                             "spoken_hook": f"The {len(items)} questions everyone asks about "
                                            f"{topic}, answered fast.",
                             "on_screen": f"{len(items)} {topic.upper()} QUESTIONS"})
        result.append({
            "topic": topic,
            "questions": [{"question": e["question"], "sources": sorted(e["sources"]),
                           "count": e["count"]} for e in items],
            "weight": sum(len(e["sources"]) + e["count"] for e in items),
            "script_ideas": ideas,
        })
    result.sort(key=lambda c: (c["topic"] == "other", -c["weight"], c["topic"]))
    return {"questions": len(qs), "merged": sum(e["count"] for e in qs) - len(qs),
            "clusters": result}


def render(r, out=sys.stdout):
    print(f"\nQUESTION CLUSTERS  ·  {r['questions']} unique questions  ·  "
          f"{len(r['clusters'])} clusters  ·  {r['merged']} duplicates merged", file=out)
    print("=" * 72, file=out)
    for c in r["clusters"]:
        n = len(c["questions"])
        print(f"\n  {c['topic'].upper()}  ({n} question{'s' if n != 1 else ''})", file=out)
        for q in c["questions"]:
            extra = f"  [{len(q['sources'])} sources]" if len(q["sources"]) > 1 else ""
            print(f"    - {q['question']}{extra}", file=out)
        print("    script ideas:", file=out)
        for i in c["script_ideas"][:4]:
            print(f"      {i['formula']:<22} \"{i['spoken_hook']}\"  /  {i['on_screen']}",
                  file=out)
    print("\n  Hand the ideas to /tt-hook for all three layers, then /tt-script.\n", file=out)


def main():
    ap = argparse.ArgumentParser(description="Cluster pasted questions into script ideas.")
    ap.add_argument("input", nargs="?", default="-", help="questions file, or - for stdin")
    ap.add_argument("--seed", default="", help="comma-separated topic words to ignore when clustering")
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
    r = cluster(read(text), [s for s in args.seed.split(",") if s.strip()])
    if not r:
        print("no questions found. Paste one question per line.", file=sys.stderr)
        sys.exit(2)
    if args.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        render(r)


if __name__ == "__main__":
    main()
