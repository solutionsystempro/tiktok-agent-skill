#!/usr/bin/env python3
# Adapted from instagram-agent-skill (c) 2026 Jake Schincariol. Modifications (c) 2026 Ian Ryan Kirk. MIT License.
"""
swipe.py - rank TikToks you collected by how far each one beat its own
account, name the hook formula, and write the swipe file.

Raw views are not evidence. A big account doing 400K had an ordinary day. A
small account doing 400K found something. This ranks on the multiple over
the account's own baseline: its median views on recent videos if you have it,
its follower count if you do not. Every row says which baseline it used, and
a batch that mixes the two says so, because those multiples are not on the
same scale.

Input is a tab- or comma-separated file you fill in by hand while you watch,
one video per row, with a header naming the columns (any order):

    account   followers   median   views   hook
    @someone  48K         11,000   412K    nobody tells you the first coat is the ugly one

Counts can be written the way TikTok shows them: 412K, 1.2M, 1,2M, 12.5k.
A cell that is not a count (for example "lots") is treated as missing and the
row is reported, not guessed at.

Optional breakdown columns, filled in by you or from the transcript:

    hook_type   the kind of opening, in your words or a hooks.json name
                (blank: the classified formula name is used)
    topic       what the video is about, a short label
    length_s    length in seconds: 34, 34s or 0:34
    structure   list, story, myth-bust, tutorial, reaction, ...
    cta         the ask at the end: follow, comment keyword, part 2, none

With those, the report aggregates the batch: the most common hook types,
topics, structures and CTAs, the median length, and which values the top
quartile by outperformance shares more than the batch as a whole.

Header aliases: creator / handle -> account, hook_text -> hook,
type -> hook_type, length / seconds / duration -> length_s, ask -> cta,
format -> structure.

Usage
  python swipe.py captured.tsv
  python swipe.py captured.csv --out ~/.claude/tiktok/swipe.md
  python swipe.py captured.tsv --json
"""

import argparse
import csv
import io
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.join(HERE, "..", "tt-hook", "hooks.json")
WORD_RE = re.compile(r"[A-Za-z0-9$%'’-]+")

try:                                              # optional: score the hooks too
    sys.path.insert(0, os.path.join(HERE, "..", "tt-hook"))
    from hookscore import run as _run_hook        # noqa: E402

    def score_hook(text):
        r = _run_hook({"spoken": text})
        # Only the spoken layer is known for a collected video, so report that.
        return round(r["layers"]["SPOKEN"]["score"], 1) if "SPOKEN" in r["layers"] else None
except Exception:                                 # tt-viral copied on its own
    score_hook = None


def load_formulas(path):
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        return None
    by_id = {h["id"]: h for h in d["hooks"]}
    order = d.get("classify_order") or sorted(by_id)
    return [(by_id[i]["id"], by_id[i]["name"],
             re.compile(by_id[i]["match"], re.IGNORECASE)) for i in order if i in by_id]


def classify(hook, formulas):
    if not formulas:
        return None, "unclassified"
    for fid, name, pattern in formulas:
        if pattern.search(hook):
            return fid, name
    return None, "unclassified"


def parse_count(cell):
    """'412000', '412,000', '412K', '1.2M', '1,2M', '12.5k views' -> int.
    Anything else -> None, never a guess."""
    s = (cell or "").strip().lower().replace(" ", "").replace(" ", "")
    s = re.sub(r"(?:views?|plays?|followers?|likes?)$", "", s)
    if not s:
        return None
    m = re.fullmatch(r"(\d+)[.,](\d{1,2})([kmb])", s)        # 1.2M or 1,2M
    if m:
        num, suffix = float(m.group(1) + "." + m.group(2)), m.group(3)
    else:
        m = re.fullmatch(r"(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?([kmb]?)", s)
        if not m:
            return None
        num = float(m.group(1).replace(",", "") + ("." + m.group(2) if m.group(2) else ""))
        suffix = m.group(3)
    mult = {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[suffix]
    return int(round(num * mult))


HEADER_ALIASES = {
    "creator": "account", "handle": "account", "username": "account",
    "hook_text": "hook", "hook text": "hook", "first line": "hook",
    "type": "hook_type", "hook type": "hook_type",
    "length": "length_s", "seconds": "length_s", "duration": "length_s", "length (s)": "length_s",
    "ask": "cta", "call to action": "cta",
    "format": "structure",
}
BREAKDOWN = ("hook_type", "topic", "structure", "cta")


def parse_seconds(cell):
    """'34', '34s', '34.5 sec', '0:34', '1:02.5', '1:02:03.25' -> seconds;
    anything else -> None."""
    s = (cell or "").strip().lower()
    m = re.fullmatch(r"(?:(\d+):)?(\d+):(\d{1,2}(?:\.\d+)?)", s)
    if m:
        hours = int(m.group(1)) if m.group(1) else 0
        return hours * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds)?", s)
    return float(m.group(1)) if m else None


def label(value):
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def read_rows(text):
    """Returns (rows, problems). Header row required: it must name views and hook."""
    text = (text or "").lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    lines = [l for l in text.split("\n") if l.strip() and not l.lstrip().startswith("#")]
    if not lines:
        return [], []
    delim = "\t" if "\t" in lines[0] else ","
    table = list(csv.reader(io.StringIO("\n".join(lines)), delimiter=delim))
    head = [c.strip().lower() for c in table[0]]
    head = [HEADER_ALIASES.get(h, h) for h in head]
    if "views" not in head or "hook" not in head:
        raise ValueError(f"header must name at least 'views' and 'hook'. Found: "
                         f"{', '.join(head) or 'nothing'}")
    rows, problems = [], []
    for n, cells in enumerate(table[1:], 2):
        cells = cells + [""] * (len(head) - len(cells))
        r = dict(zip(head, [c.strip() for c in cells]))
        views = parse_count(r.get("views"))
        if not views or not r.get("hook"):
            problems.append(f"line {n}: skipped, " + ("no hook" if views else
                            f"views \"{r.get('views', '')}\" is not a count"))
            continue
        r["views"] = views
        for k in ("followers", "median"):
            raw = r.get(k)
            r[k] = parse_count(raw)
            if raw and r[k] is None:
                problems.append(f"line {n}: {k} \"{raw}\" is not a count, ignored")
        raw_len = r.get("length_s")
        r["length_s"] = parse_seconds(raw_len)
        if raw_len and r["length_s"] is None:
            problems.append(f"line {n}: length_s \"{raw_len}\" is not a number of seconds, ignored")
        for k in BREAKDOWN:
            r[k] = label(r.get(k))
        rows.append(r)
    return rows, problems


def tally(items, key):
    counts = {}
    for r in items:
        v = r.get(key)
        if v and v != "unclassified":
            counts[v] = counts.get(v, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def breakdown(ranked):
    """Aggregate the breakdown fields across the batch, and compare the top
    quartile by outperformance against the whole batch.

    A value 'stands out' in the top quartile when it appears in at least two
    top-quartile posts (or the only one, for a quartile of one) and its share
    there is higher than its share of the whole batch."""
    for r in ranked:
        r["hook_type_used"] = r.get("hook_type") or (
            label(r["formula"]) if r.get("formula") not in (None, "unclassified") else "")
    scored = [r for r in ranked if r.get("outlier")]
    q = max(1, -(-len(scored) // 4)) if scored else 0          # ceil(n / 4)
    top = scored[:q]
    out = {"posts": len(ranked), "top_quartile_size": q, "fields": {}}
    for key, name in (("hook_type_used", "hook_type"), ("topic", "topic"),
                      ("structure", "structure"), ("cta", "cta")):
        everyone = tally(ranked, key)
        filled = sum(1 for r in ranked if r.get(key))
        top_counts = dict(tally(top, key))
        top_filled = sum(1 for r in top if r.get(key))
        stands_out = []
        for value, n_top in sorted(top_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            share_top = n_top / top_filled if top_filled else 0
            share_all = dict(everyone)[value] / filled if filled else 0
            if (n_top >= 2 or q == 1) and share_top > share_all:
                stands_out.append({"value": value, "top": n_top, "top_share": round(share_top, 2),
                                   "all_share": round(share_all, 2)})
        out["fields"][name] = {"filled": filled, "most_common": everyone[:5],
                               "top_quartile": sorted(top_counts.items(),
                                                      key=lambda kv: (-kv[1], kv[0]))[:5],
                               "stands_out": stands_out}
    lengths = [r["length_s"] for r in ranked if r.get("length_s") is not None]
    top_lengths = [r["length_s"] for r in top if r.get("length_s") is not None]
    out["median_length_s"] = round(statistics.median(lengths), 1) if lengths else None
    out["top_quartile_median_length_s"] = (round(statistics.median(top_lengths), 1)
                                           if top_lengths else None)
    return out


def analyse(rows, formulas):
    for r in rows:
        if r.get("median"):
            base, source = r["median"], "median"
        elif r.get("followers"):
            base, source = r["followers"], "followers"
        else:
            base, source = 0, None
        r["baseline"], r["baseline_source"] = base, source
        r["outlier"] = round(r["views"] / base, 2) if base else None
        r["formula_id"], r["formula"] = classify(r["hook"], formulas)
        r["words"] = len(WORD_RE.findall(r["hook"]))
        r["hook_score"] = score_hook(r["hook"]) if score_hook else None
    ranked = sorted(rows, key=lambda r: -(r["outlier"] or 0))
    third = max(1, len(ranked) // 3)
    top, bottom = ranked[:third], ranked[-third:]

    def med(items, key):
        vals = [i[key] for i in items if i.get(key) is not None]
        return round(statistics.median(vals), 1) if vals else None

    counts = {}
    for r in top:
        counts[r["formula"]] = counts.get(r["formula"], 0) + 1
    by_median = sum(1 for r in ranked if r["baseline_source"] == "median")
    by_followers = sum(1 for r in ranked if r["baseline_source"] == "followers")
    if by_median and not by_followers:
        baseline = "account median"
    elif by_followers and not by_median:
        baseline = "follower count"
    elif by_median and by_followers:
        baseline = f"mixed ({by_median} account median, {by_followers} follower count)"
    else:
        baseline = "none"
    return {
        "baseline": baseline,
        "baseline_counts": {"median": by_median, "followers": by_followers,
                            "none": len(ranked) - by_median - by_followers},
        "n": len(ranked),
        "accounts": len({r.get("account", "") for r in ranked}),
        "videos": ranked,
        "top_formulas": sorted(counts.items(), key=lambda kv: -kv[1]),
        "top_hook_score": med(top, "hook_score"),
        "bottom_hook_score": med(bottom, "hook_score"),
        "top_words": med(top, "words"),
        "bottom_words": med(bottom, "words"),
        "unclassified": sum(1 for r in ranked if r["formula"] == "unclassified"),
        "breakdown": breakdown(ranked),
    }


def breakdown_lines(b):
    """Plain-text lines for the breakdown, shared by the console and markdown."""
    lines = [f"top quartile = {b['top_quartile_size']} of {b['posts']} posts by multiple"]
    for name, f in b["fields"].items():
        if not f["filled"]:
            lines.append(f"{name}: not filled in")
            continue
        common = ", ".join(f"{v} x{c}" for v, c in f["most_common"])
        lines.append(f"{name} ({f['filled']} filled): {common}")
        for s in f["stands_out"]:
            lines.append(f"  top quartile leans {name} = {s['value']}: {s['top']} posts, "
                         f"{s['top_share']:.0%} of the top vs {s['all_share']:.0%} overall")
    if b["median_length_s"] is not None:
        lines.append(f"median length: {b['median_length_s']}s overall, "
                     f"{b['top_quartile_median_length_s']}s in the top quartile")
    return lines


def render(a, out=sys.stdout):
    head = (f"SWIPE FILE  ·  {a['n']} videos  ·  {a['accounts']} accounts  ·  "
            f"baseline: {a['baseline']}")
    print("\n" + head, file=out)
    print("=" * max(len(head), 78), file=out)
    for r in a["videos"]:
        mult = f"{r['outlier']:.1f}x" if r["outlier"] else "   ?"
        score = f"{r['hook_score']:.0f}" if r["hook_score"] is not None else " -"
        fid = f"#{r['formula_id']:<2}" if r["formula_id"] else "-  "
        src = {"median": "med", "followers": "fol"}.get(r["baseline_source"], " - ")
        print(f"  {mult:>7} {src}  hook {score:>3}  {fid} {r['formula'][:20]:<20} "
              f"{r.get('account', '')[:16]:<16} {r['views']:>11,}", file=out)
        print(f"           \"{r['hook'][:96]}\"", file=out)
    print("-" * max(len(head), 78), file=out)
    print("  med = multiple over account median, fol = over follower count.", file=out)
    print("WHAT IS WORKING IN THIS BATCH", file=out)
    if a["top_formulas"]:
        print("  top third by multiple:  "
              + ", ".join(f"{n} x{c}" for n, c in a["top_formulas"][:4]), file=out)
    if a["top_hook_score"] is not None:
        print(f"  median spoken-hook score: top {a['top_hook_score']:.0f}  "
              f"vs bottom {a['bottom_hook_score']:.0f}", file=out)
    print(f"  median hook length:    top {a['top_words']} words  "
          f"vs bottom {a['bottom_words']} words", file=out)
    print(f"  unclassified:          {a['unclassified']} of {a['n']}. Read those by hand.",
          file=out)
    print("BREAKDOWN", file=out)
    for line in breakdown_lines(a["breakdown"]):
        print(f"  {line}", file=out)
    print("\n  A hand-collected batch is a sample, not proof. Collect more before you "
          "believe a pattern.\n", file=out)


SOURCE_LABEL = {"median": "account median", "followers": "follower count"}


def to_markdown(a):
    lines = ["# TikTok swipe file", "",
             f"{a['n']} videos across {a['accounts']} accounts. "
             f"Ranked by multiple over {a['baseline']}.", ""]
    for r in a["videos"]:
        mult = f"{r['outlier']:.1f}x" if r["outlier"] else "?"
        lines += [f"## {mult}  {r['formula']}  ({r.get('account', '')})",
                  f"- views: {r['views']:,}  baseline: {r['baseline']:,} "
                  f"({SOURCE_LABEL.get(r['baseline_source'], 'none')})",
                  f"- spoken-hook score: {r['hook_score']}  words: {r['words']}",
                  f"- hook: \"{r['hook']}\""]
        extra = [f"{k}: {r[k]}" for k in ("hook_type", "topic", "structure", "cta") if r.get(k)]
        if r.get("length_s") is not None:
            extra.append(f"length: {r['length_s']:g}s")
        if extra:
            lines.append("- " + "  ".join(extra))
        lines.append("")
    lines += ["## Breakdown", ""] + [f"- {l}" for l in breakdown_lines(a["breakdown"])]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Rank collected TikToks by outlier multiple.")
    ap.add_argument("input", nargs="?", default="-", help="TSV or CSV file, or - for stdin")
    ap.add_argument("--hooks", default=HOOKS, help="path to tt-hook/hooks.json")
    ap.add_argument("--out", help="also write the swipe file as markdown here")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):   # Windows pipes default to cp1252
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        if args.input == "-":
            text = sys.stdin.read()
        else:
            with open(args.input, encoding="utf-8-sig", newline="") as fh:
                text = fh.read()
        rows, problems = read_rows(text)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
    for p in problems:
        print(f"note: {p}", file=sys.stderr)
    if not rows:
        print("no usable rows. Need a header naming views and hook, and at least one row "
              "with both.", file=sys.stderr)
        sys.exit(2)
    formulas = load_formulas(args.hooks)
    a = analyse(rows, formulas)
    if not formulas:
        print("note: hooks.json not found, formulas not named. Pass --hooks.", file=sys.stderr)
    if score_hook is None:
        print("note: hookscore.py not importable, hook scores skipped.", file=sys.stderr)
    if args.json:
        print(json.dumps(a, indent=2, ensure_ascii=False))
    else:
        render(a)
    if args.out:
        path = os.path.expanduser(args.out)
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(to_markdown(a))
        print(f"wrote {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
