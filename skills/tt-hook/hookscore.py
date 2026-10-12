#!/usr/bin/env python3
# Adapted from instagram-agent-skill (c) 2026 Jake Schincariol. Modifications (c) 2026 Ian Ryan Kirk. MIT License.
"""
hookscore.py - score the first one to three seconds of a TikTok as three
layers: the spoken line, the on-screen text, and the first visual.

A TikTok hook is not one sentence. In the same opening seconds the viewer
hears a line, reads a line, and sees a frame, and each of those can hold or
lose them. This scores each layer on its own, then combines them, with the
weakest layer weighted heavily: one empty layer is enough to lose a thumb.

What this is:  local heuristics, computed from your text alone.
  SPOKEN     length you can say in about three seconds, a concrete marker,
             something at stake, the payload near the front, a viewer to aim
             at. These five checks come from the instagram-agent-skill hook
             scorer.
  ON-SCREEN  short enough to read at a glance, concrete, adds something the
             spoken line does not, no hashtags or emoji-only cards.
  VISUAL     your written description of frame one: is something moving or
             already shown, is there a concrete subject, does it avoid the
             static openers (a logo, a title card, a still face waiting).
             It scores the sentence you wrote about the frame, not the frame.

What this is NOT:  a view predictor. None of these weights were fitted to
TikTok performance data. Use it to catch the weak hooks before you film them,
then trust your own retention numbers in TikTok Studio (/tt-retention).

Input
  A file of hooks. Either one spoken line per line (the other layers are then
  reported as missing), or blocks separated by a blank line with prefixes:

      spoken: This chair cost $1,400. Here is what that buys you.
      text: $1,400 CHAIR. WORTH IT?
      visual: Hand slaps the price sticker onto the chair.

  `on-screen:`, `onscreen:` and `screen:` also work for the text layer, and
  `frame:` for the visual. A line with no prefix inside a block is spoken.

Usage
  python hookscore.py hooks.txt
  python hookscore.py --spoken "..." --text "..." --visual "..."
  python hookscore.py hooks.txt --json
  type hooks.txt | python hookscore.py -
"""

import argparse
import json
import re
import statistics
import sys

WORD_RE = re.compile(r"[A-Za-z0-9$%'’-]+")
NUMBER_RE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?"
    r"|\b\d[\d,]*(?:\.\d+)?\s?"
    r"(?:%|k\b|x\b|hrs?\b|hours?\b|mins?\b|minutes?\b|secs?\b|seconds?\b"
    r"|days?\b|weeks?\b|months?\b|years?\b)?",
    re.IGNORECASE)
PROPER_RE = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z]{2,}\b")
HASHTAG_RE = re.compile(r"(?:^|\s)#\w+")
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")

# Spoken hooks say their numbers out loud, so "zero dollars" counts as
# concrete. "one" and "first" are left out: they are filler far more often.
SPOKEN_NUMBERS = {
    "zero", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "fifteen", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million",
    "billion", "dozen", "half", "twice", "triple",
}
MONEY_WORDS = {
    "dollars", "dollar", "bucks", "grand", "percent", "cents", "pounds",
    "euros", "rent", "salary", "profit", "revenue",
}

STAKES = {
    "stop", "never", "wrong", "mistake", "mistakes", "lost", "lose", "losing",
    "cost", "costs", "broke", "broken", "failed", "fail", "nobody", "no",
    "not", "don't", "dont", "doesn't", "didn't", "can't", "won't", "quit",
    "fired", "deleted", "killed", "ruined", "ruin", "ruins", "replaced", "cut",
    "free", "paid", "saved", "banned", "worst", "best", "hate", "wasted",
    "waste", "scam", "lie", "truth", "secret", "hidden", "before", "until",
    "instead", "but", "except", "unless", "problem", "risk", "warning",
    "regret", "should", "still", "only", "without", "versus", "vs", "actually",
    "tested", "tried", "dense", "dirty", "broken", "late", "left", "danger",
}

WEAK_OPENERS = [
    "so", "ok", "okay", "hey", "hi", "hello", "guys", "yo", "alright",
    "welcome", "today", "basically", "honestly", "um", "uh", "just", "let",
    "lets", "let's", "i wanted", "i want", "one of", "in this", "in today",
    "the thing", "a lot", "there is a lot", "this is a video", "it is",
    "as a reminder", "you know",
]

IMPERATIVES = {
    "stop", "steal", "copy", "delete", "try", "watch", "read", "save",
    "use", "build", "make", "write", "send", "take", "start", "quit",
    "never", "always", "don't", "dont", "do", "put", "check", "look",
}

DEALBREAKERS = [
    (re.compile(r"(?i)^\s*(?:stop scrolling|don'?t scroll|wait[,.]? don'?t scroll)"),
     "Opens with \"stop scrolling\". Asking for attention is not a reason to stay."),
    (re.compile(r"(?i)\b(?:in (?:this|today'?s) (?:video|tiktok)|i'?m going to show you|i'?ll show you how)\b"),
     "Video preamble. Delete it and open on the payoff."),
    (re.compile(r"(?i)^\s*(?:hey |hi |what'?s up |welcome )"),
     "Greeting. The first second is too expensive to spend on hello."),
    (re.compile(r"(?i)\bwait (?:for it|till the end|until the end)\b|\bwatch till the end\b"),
     "\"Wait for it\". Holding the payoff hostage tells the viewer there is nothing yet."),
    (HASHTAG_RE, "Hashtag in the spoken hook. Hashtags belong in the caption."),
]

# First-visual vocabulary. Motion verbs and "result shown" words suggest the
# frame is doing work. Static openers suggest it is not.
MOTION = {
    "slap", "slaps", "drop", "drops", "dropped", "pour", "pours", "pouring",
    "cut", "cuts", "cutting", "throw", "throws", "slam", "slams", "slammed",
    "rip", "rips", "tear", "tears", "open", "opens", "opening", "spin",
    "spins", "walk", "walks", "walking", "run", "runs", "running", "grab",
    "grabs", "hand", "hands", "hold", "holds", "holding", "held", "point",
    "points", "pointing", "zoom", "zooms", "push", "pushes", "pull", "pulls",
    "flip", "flips", "reveal", "reveals", "lift", "lifts", "splash",
    "crash", "burst", "fall", "falls", "mid-stroke", "mid", "already",
    "moving", "move", "moves", "swipe", "swipes", "tap", "taps", "thumb",
    "hovering", "starting", "start", "starts", "slide", "slides", "smash",
    "press", "presses", "mixing", "stir", "stirs", "close-up", "closeup",
    "whip", "pan", "pans", "tracking", "handheld",
}
RESULT = {
    "finished", "result", "results", "after", "before", "final", "done",
    "side", "both", "next", "versus", "vs", "full", "line-up", "lineup",
    "stain", "problem", "symptom", "price", "sticker", "label", "labelled",
    "labeled", "timer", "clock", "comment", "screen", "message", "contract",
}
STATIC = [
    (re.compile(r"(?i)\b(?:logo|intro|title card|title screen|black screen|blank screen|"
                r"channel art|animated intro|bumper)\b"),
     "the first frame is a logo, intro or title card"),
    (re.compile(r"(?i)\b(?:talking head|sitting (?:still|at a desk|on (?:a|the) (?:couch|sofa|chair))|"
                r"looking at (?:the )?camera|face to camera|waves? (?:at|to) (?:the )?camera|"
                r"says hi|smiles at)\b"),
     "the first frame is a still face waiting to talk"),
    (re.compile(r"(?i)\b(?:static|still shot|wide shot of (?:a|the) room|establishing shot|"
                r"slow fade|fades? in)\b"),
     "the first frame is a slow or static establishing shot"),
]

STOP = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "that", "this", "it", "is", "are", "was", "be", "you", "your", "i", "my",
    "me", "we", "our", "so", "just", "do", "at", "as", "by", "from", "what",
    "here", "how", "why", "if", "not", "no",
}


def clamp(n):
    return max(0.0, min(100.0, n))


def words(text):
    # "$18,000" is one word when it is spoken, so it is one word here too.
    return WORD_RE.findall(re.sub(r"(?<=\d),(?=\d)", "", text or ""))


def _low(text):
    return [w.lower().strip("'’") for w in words(text)]


# ---------------------------------------------------------------- spoken

def check_length(text):
    """About three seconds to say at ~165 words per minute, so eight words or fewer."""
    n = len(words(text))
    secs = n / 2.75                      # ~165 words per minute
    if 4 <= n <= 8:
        score = 100.0
    elif n < 4:
        score = clamp(100 - (4 - n) * 20)
    else:
        score = clamp(100 - (n - 8) * 10)
    return score, f"{n} words, ~{secs:.1f}s spoken (want 4-8 words, about 3s)"


def check_specificity(text):
    nums = [n.strip() for n in NUMBER_RE.findall(text or "") if n.strip()]
    propers = set(PROPER_RE.findall(text or ""))
    spoken = [w for w in _low(text) if w in SPOKEN_NUMBERS or w in MONEY_WORDS]
    hits = len(nums) + len(propers) + len(spoken)
    score = 15.0 if hits == 0 else clamp(45 + hits * 30)
    found = ", ".join(nums[:2] + sorted(propers)[:2] + spoken[:2])
    return score, (f"{hits} concrete marker(s)" + (f": {found}" if found else
                   ", no number, no name, nothing checkable"))


def check_stakes(text):
    markers = sorted({w for w in _low(text) if w in STAKES})
    if re.search(r"\$\s?\d", text or ""):
        markers.append("a price")
    n = len(markers)
    score = {0: 20.0, 1: 70.0}.get(n, 100.0)
    return score, (f"{n} tension marker(s)" + (f": {', '.join(markers[:4])}" if markers
                                               else ", nothing is at stake in this line"))


def check_frontload(text):
    w = words(text)
    if not w:
        return 0.0, "empty"
    low = _low(text)
    opener = " ".join(low[:3])
    penalty, hit = 0, None
    for weak in WEAK_OPENERS:
        if opener == weak or opener.startswith(weak + " ") or low[0] == weak:
            penalty, hit = 30, weak
            break
    payload = None
    for i, token in enumerate(low):
        if (token in STAKES or token in SPOKEN_NUMBERS or token in MONEY_WORDS
                or NUMBER_RE.match(w[i]) or (i and PROPER_RE.match(w[i]))):
            payload = i
            break
    if payload is None:
        base, where = 30.0, "no payload word anywhere in the line"
    elif payload <= 3:
        base, where = 100.0, f"payload at word {payload + 1}"
    elif payload <= 6:
        base, where = 70.0, f"payload at word {payload + 1}, could move forward"
    else:
        base, where = 40.0, f"payload at word {payload + 1}, too late"
    return clamp(base - penalty), where + (f"; weak opener \"{hit}\"" if hit else "")


def check_address(text):
    low = (text or "").lower()
    w = _low(text)
    if re.search(r"\b(you|your|you're|youre|yourself)\b", low):
        return 100.0, "speaks to the viewer"
    if w and w[0] in IMPERATIVES:
        return 90.0, f"imperative opener (\"{w[0]}\")"
    if w and w[0] == "pov":
        return 90.0, "POV puts the viewer in the scene"
    if re.search(r"\b(i|my|me|we|our)\b", low):
        return 70.0, "first person, no viewer named"
    return 35.0, "third person, nobody in the room"


SPOKEN_CHECKS = ["LENGTH", "SPECIFICITY", "STAKES", "FRONTLOAD", "ADDRESS"]


def score_spoken(text):
    checks = {
        "LENGTH": check_length(text),
        "SPECIFICITY": check_specificity(text),
        "STAKES": check_stakes(text),
        "FRONTLOAD": check_frontload(text),
        "ADDRESS": check_address(text),
    }
    flags = [msg for pattern, msg in DEALBREAKERS if pattern.search(text or "")]
    scores = [checks[c][0] for c in SPOKEN_CHECKS]
    layer = clamp(statistics.mean(scores) * 0.6 + min(scores) * 0.4)
    return layer, checks, flags


# ---------------------------------------------------------------- on-screen

def score_onscreen(text, spoken=""):
    checks, flags = {}, []
    n = len(words(text))
    if n == 0 and EMOJI_RE.search(text or ""):
        checks["GLANCE"] = (20.0, "emoji only, nothing to read")
    elif n <= 6:
        checks["GLANCE"] = (100.0, f"{n} words, readable at a glance")
    elif n <= 9:
        checks["GLANCE"] = (65.0, f"{n} words, more than a glance. Aim for six")
    else:
        checks["GLANCE"] = (clamp(65 - (n - 9) * 12), f"{n} words, a paragraph on screen")

    hits = len([x for x in NUMBER_RE.findall(text or "") if x.strip()]) \
        + len([w for w in _low(text) if w in SPOKEN_NUMBERS or w in MONEY_WORDS]) \
        + len(re.findall(r"\b[A-Z]{2,}\b", text or "")) // 3
    checks["CONCRETE"] = ((100.0, f"{hits} concrete marker(s)") if hits
                          else (45.0, "no number or named thing"))

    s_words = {w for w in _low(spoken) if w not in STOP}
    t_words = {w for w in _low(text) if w not in STOP}
    if not spoken.strip():
        checks["ADDS"] = (70.0, "no spoken line to compare against")
    elif not t_words:
        checks["ADDS"] = (40.0, "nothing to compare")
    elif t_words <= s_words and len(t_words) >= 4:
        checks["ADDS"] = (40.0, "repeats the spoken line word for word. Make it shorter or "
                                "say the other half")
    elif t_words & s_words:
        checks["ADDS"] = (100.0, f"shares \"{sorted(t_words & s_words)[0]}\" with the spoken "
                                 "line and adds the rest")
    else:
        checks["ADDS"] = (75.0, "no shared word with the spoken line. Fine if it is "
                                "the other half of the same idea")

    if HASHTAG_RE.search(text or ""):
        flags.append("Hashtag in the on-screen text. It reads as a label, not a hook.")
    scores = [v[0] for v in checks.values()]
    layer = clamp(statistics.mean(scores) * 0.6 + min(scores) * 0.4)
    return layer, checks, flags


# ---------------------------------------------------------------- visual

def score_visual(text):
    checks, flags = {}, []
    low = _low(text)
    motion = sorted({w for w in low if w in MOTION})
    result = sorted({w for w in low if w in RESULT})
    if motion:
        checks["MOTION"] = (100.0, f"movement in frame one: {', '.join(motion[:3])}")
    elif result:
        checks["MOTION"] = (75.0, "no movement named, but the result or problem is shown")
    else:
        checks["MOTION"] = (35.0, "nothing moving and nothing shown yet")
    if result or re.search(r"\b\d", text or ""):
        checks["SHOWS IT"] = (100.0, "frame one shows the thing itself"
                              + (f" ({', '.join(result[:2])})" if result else ""))
    else:
        content = [w for w in low if w not in STOP]
        checks["SHOWS IT"] = ((70.0, "names a subject") if len(content) >= 2
                              else (30.0, "too vague to picture"))
    static = [msg for pattern, msg in STATIC if pattern.search(text or "")]
    for msg in static:
        flags.append(f"Static opener: {msg}.")
    checks["NOT STATIC"] = ((40.0, static[0]) if static else (100.0, "no static opener named"))
    scores = [v[0] for v in checks.values()]
    layer = clamp(statistics.mean(scores) * 0.6 + min(scores) * 0.4)
    return layer, checks, flags


# ---------------------------------------------------------------- combined

LAYERS = ["SPOKEN", "ON-SCREEN", "VISUAL"]
WEIGHTS = {"SPOKEN": 0.45, "ON-SCREEN": 0.30, "VISUAL": 0.25}
MISSING_PENALTY = 10


def run(hook):
    """hook: dict with optional keys spoken, text, visual. Returns a result dict."""
    spoken = (hook.get("spoken") or "").strip()
    text = (hook.get("text") or "").strip()
    visual = (hook.get("visual") or "").strip()
    layers, flags, missing = {}, [], []
    if spoken:
        s, c, f = score_spoken(spoken)
        layers["SPOKEN"] = {"score": s, "checks": c}
        flags += f
    else:
        missing.append("SPOKEN")
    if text:
        s, c, f = score_onscreen(text, spoken)
        layers["ON-SCREEN"] = {"score": s, "checks": c}
        flags += f
    else:
        missing.append("ON-SCREEN")
    if visual:
        s, c, f = score_visual(visual)
        layers["VISUAL"] = {"score": s, "checks": c}
        flags += f
    else:
        missing.append("VISUAL")
    if not layers:
        return {"hook": hook, "layers": {}, "missing": missing, "flags": ["Empty hook."],
                "score": 0.0, "verdict": "WEAK", "weakest": None}
    total_w = sum(WEIGHTS[k] for k in layers)
    weighted = sum(layers[k]["score"] * WEIGHTS[k] for k in layers) / total_w
    lowest = min(v["score"] for v in layers.values())
    overall = clamp(weighted * 0.6 + lowest * 0.4 - len(flags) * 15
                    - len(missing) * MISSING_PENALTY)
    weakest = min(layers, key=lambda k: layers[k]["score"])
    if overall >= 70 and lowest >= 55 and not flags and not missing:
        verdict = "STRONG"
    elif overall >= 50:
        verdict = "OK"
    else:
        verdict = "WEAK"
    return {"hook": hook, "layers": layers, "missing": missing, "flags": flags,
            "score": overall, "verdict": verdict, "weakest": weakest}


PREFIXES = {
    "spoken": "spoken", "say": "spoken", "voice": "spoken", "vo": "spoken",
    "text": "text", "on-screen": "text", "onscreen": "text", "on screen": "text",
    "screen": "text", "visual": "visual", "frame": "visual", "first frame": "visual",
}
PREFIX_RE = re.compile(r"(?i)^\s*(" + "|".join(sorted((re.escape(k) for k in PREFIXES),
                                                      key=len, reverse=True)) + r")\s*:\s*(.*)$")


def parse(raw):
    """Turn file text into a list of hook dicts."""
    raw = (raw or "").replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    lines = raw.split("\n")
    if not any(PREFIX_RE.match(l) for l in lines):
        return [{"spoken": l.strip()} for l in lines if l.strip()]
    hooks, cur = [], {}
    for line in lines + [""]:
        if not line.strip():
            if cur:
                hooks.append(cur)
                cur = {}
            continue
        m = PREFIX_RE.match(line)
        key, value = (PREFIXES[m.group(1).lower()], m.group(2).strip()) if m \
            else ("spoken", line.strip())
        cur[key] = (cur.get(key, "") + " " + value).strip()
    return hooks


def bar(score, width=20):
    filled = round(score / 100 * width)
    return "#" * filled + "." * (width - filled)


def label(hook):
    return hook.get("spoken") or hook.get("text") or hook.get("visual") or ""


def render_one(r, out=sys.stdout):
    print("\nHOOK SCORE  (three layers)", file=out)
    print("=" * 66, file=out)
    for key, name in (("spoken", "SPOKEN"), ("text", "ON-SCREEN"), ("visual", "VISUAL")):
        print(f"  {name:<10} {r['hook'].get(key) or '(missing)'}", file=out)
    for name in LAYERS:
        print("", file=out)
        if name not in r["layers"]:
            print(f"  {name:<10} MISSING  (-{MISSING_PENALTY}). Write this layer.", file=out)
            continue
        layer = r["layers"][name]
        print(f"  {name:<10} {bar(layer['score'])} {layer['score']:5.1f}", file=out)
        for check, (score, detail) in layer["checks"].items():
            print(f"    {check:<12} {score:5.1f}  {detail}", file=out)
    print("-" * 66, file=out)
    print(f"  {'HOOK':<10} {bar(r['score'])} {r['score']:5.1f}   {r['verdict']}", file=out)
    for f in r["flags"]:
        print(f"  DEALBREAKER  {f}", file=out)
    if r["verdict"] != "STRONG" and r["weakest"]:
        print(f"\n  Weakest layer: {r['weakest']}. Fix that one and re-run.", file=out)
    print("", file=out)


def render_table(rows, out=sys.stdout):
    print("\nHOOK RANKING  (spoken / on-screen / visual)\n" + "=" * 78, file=out)
    for i, r in enumerate(rows, 1):
        mark = "->" if i == 1 else "  "
        text = label(r["hook"])
        text = text if len(text) <= 52 else text[:49] + "..."
        parts = " ".join(f"{r['layers'][k]['score']:3.0f}" if k in r["layers"] else "  -"
                         for k in LAYERS)
        print(f"{mark} {r['score']:5.1f} {r['verdict']:<6} [{parts}]  {text}", file=out)
        if r["missing"]:
            print(f"        missing: {', '.join(r['missing'])}", file=out)
        for f in r["flags"]:
            print(f"        dealbreaker: {f}", file=out)
    print("\nFilm the top one. If the top one is under 50, none of these is the hook yet.\n",
          file=out)


def to_json(r):
    return {
        "hook": r["hook"],
        "layers": {k: {"score": round(v["score"], 1),
                       "checks": {c: {"score": round(s, 1), "detail": d}
                                  for c, (s, d) in v["checks"].items()}}
                   for k, v in r["layers"].items()},
        "missing": r["missing"], "flags": r["flags"],
        "score": round(r["score"], 1), "verdict": r["verdict"], "weakest": r["weakest"],
    }


def main():
    ap = argparse.ArgumentParser(description="Score a TikTok hook on three layers.")
    ap.add_argument("input", nargs="?", default=None, help="hooks file, or - for stdin")
    ap.add_argument("--spoken", help="the spoken first line")
    ap.add_argument("--text", help="the on-screen text in the first seconds")
    ap.add_argument("--visual", help="a description of the first frame")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):   # Windows pipes default to cp1252
            stream.reconfigure(encoding="utf-8", errors="replace")
    if args.spoken or args.text or args.visual:
        hooks = [{"spoken": args.spoken or "", "text": args.text or "",
                  "visual": args.visual or ""}]
    else:
        src = args.input or "-"
        if src == "-":
            raw = sys.stdin.read()
        else:
            with open(src, encoding="utf-8-sig") as fh:
                raw = fh.read()
        hooks = parse(raw)
    if not hooks:
        print("nothing to score", file=sys.stderr)
        sys.exit(2)

    results = [run(h) for h in hooks]
    if args.json:
        payload = [to_json(r) for r in results]
        print(json.dumps(payload if len(payload) > 1 else payload[0], indent=2,
                         ensure_ascii=False))
    elif len(results) == 1:
        render_one(results[0])
    else:
        render_table(sorted(results, key=lambda r: -r["score"]))
    sys.exit(0 if max(r["score"] for r in results) >= 70 else 1)


if __name__ == "__main__":
    main()
