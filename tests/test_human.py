# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
import os
import unittest

from helpers import load, run_cli, temp_file

humanize = load("tt-human", "humanize")
detect = load("tt-human", "detect")
LEX = humanize.load_lexicon()

SLOP = (
    "In today’s fast-paced world, it’s crucial to leverage robust, seamless "
    "solutions — delve into the transformative landscape. Moreover, unlock the "
    "potential of innovation. Furthermore, embrace a holistic paradigm. Additionally, "
    "navigate the ever-evolving journey. Wait for it. Follow for part 2! #fyp #viral"
)
HUMAN = (
    "My starter died twice in March. Third try, I switched to rye flour and kept it on "
    "top of the fridge, where it's warmer. It doubled in nine hours. I didn't change "
    "anything else. You'll probably kill one too. Mine cost me $4 of flour each time, "
    "so it's a cheap lesson."
)


def clean(text):
    return humanize.humanize(text, LEX)[0]


class HumanizeTest(unittest.TestCase):
    def test_strips_em_dash_slop_and_invisibles(self):
        out, report = humanize.humanize("We leverage robust tools — it’s crucial.​", LEX)
        for bad in ("—", "​", "’", "leverage"):
            self.assertNotIn(bad, out.lower())
        self.assertTrue(report["lexical"])
        self.assertTrue(report["invisible"])

    def test_tiktok_bait_is_removed_or_flagged(self):
        out, report = humanize.humanize("Bread in 3 steps. Follow for part 2!", LEX)
        self.assertNotIn("part 2", out.lower())
        self.assertEqual(out, "Bread in 3 steps.\n")          # no stranded "!"
        flags = {s["name"] for s in humanize.humanize("Like this for part two.\n#fyp #foryou",
                                                      LEX)[1]["structures"]}
        self.assertIn("Part 2 bait", flags)
        self.assertIn("Filler hashtag (#fyp, #foryou, #viral)", flags)

    def test_question_mark_kept_when_real(self):
        self.assertEqual(clean("Really?! It worked."), "Really?! It worked.\n")

    def test_urls_untouched(self):
        url = "https://example.com/leverage—robust"
        self.assertIn(url, clean(f"See {url} for more."))

    def test_leading_ellipsis_survives(self):
        self.assertEqual(clean("...and then it doubled."), "...and then it doubled.\n")

    def test_crlf_bom_and_empty(self):
        self.assertEqual(clean("﻿Line one\r\nLine two — done\r\n"),
                         "Line one\nLine two, done\n")
        out, report = humanize.humanize("", LEX)
        self.assertEqual(out, "\n")
        self.assertFalse(any(report.values()))

    def test_cli_emoji_through_a_pipe(self):
        p = run_cli("tt-human", "humanize.py", "-", stdin="Done \U0001F35E — really.\n")
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        self.assertEqual(p.stdout.decode("utf-8").replace("\r\n", "\n"),
                         "Done \U0001F35E, really.\n")


class DetectTest(unittest.TestCase):
    def test_human_text_scores_above_slop(self):
        _, slop_score, slop_verdict = detect.run(SLOP, LEX)
        _, human_score, _ = detect.run(HUMAN, LEX)
        self.assertGreater(human_score, slop_score + 20)
        self.assertEqual(slop_verdict, "FLAGGED")

    def test_humanize_improves_the_score(self):
        _, before, _ = detect.run(SLOP, LEX)
        _, after, _ = detect.run(clean(SLOP), LEX)
        self.assertGreater(after, before)

    def test_empty_and_range(self):
        results, overall, verdict = detect.run("", LEX)
        self.assertEqual(set(results), set(detect.CHECKS))
        self.assertIn(verdict, ("PASS", "REVIEW", "FLAGGED"))
        results, overall, _ = detect.run(SLOP + "​" * 20, LEX)
        for score, _ in results.values():
            self.assertTrue(0 <= score <= 100)

    def test_cli_compare_with_bom_file(self):
        a = temp_file(SLOP, raw=("﻿" + SLOP).encode("utf-8"))
        b = temp_file(clean(SLOP))
        try:
            p = run_cli("tt-human", "detect.py", a, b)
            self.assertIn(p.returncode, (0, 1), p.stderr.decode("utf-8", "replace"))
            self.assertIn("->", p.stdout.decode("utf-8"))
        finally:
            os.remove(a)
            os.remove(b)


if __name__ == "__main__":
    unittest.main()
