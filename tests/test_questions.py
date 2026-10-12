# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
import json
import unittest

from helpers import load, run_cli

questions = load("tt-seo", "questions")

PASTED = ("﻿# tiktok search suggestions\r\n"
          "how to keep sourdough starter alive\r\n"
          "why is my sourdough starter not rising\r\n"
          "how often to feed sourdough starter\r\n"
          "# people also ask\r\n"
          "How often do you feed a sourdough starter?\r\n"
          "Why is my sourdough bread dense?\r\n"
          "1. How do you fix dense bread?\r\n"
          "Can you freeze sourdough discard?\r\n"
          "what flour is best for sourdough starter\r\n")


class QuestionsTest(unittest.TestCase):
    def setUp(self):
        self.r = questions.cluster(questions.read(PASTED), ["sourdough"])
        self.by = {c["topic"]: c for c in self.r["clusters"]}

    def test_clusters_by_shared_topic_word(self):
        self.assertEqual(set(self.by), {"starter", "bread", "other"})
        self.assertEqual(len(self.by["starter"]["questions"]), 4)
        self.assertEqual(len(self.by["bread"]["questions"]), 2)
        self.assertEqual(self.r["clusters"][-1]["topic"], "other")

    def test_near_duplicates_merge_across_sources(self):
        self.assertEqual(self.r["merged"], 1)
        top = self.by["starter"]["questions"][0]
        self.assertEqual(top["sources"], ["people also ask", "tiktok search suggestions"])
        self.assertEqual(top["count"], 2)

    def test_script_ideas(self):
        ideas = self.by["starter"]["script_ideas"]
        self.assertEqual(ideas[0]["formula"], "#6 Numbered Lessons")
        self.assertEqual(sum(1 for i in ideas if i["formula"].startswith("#5")), 4)
        bread = self.by["bread"]["script_ideas"]
        self.assertTrue(all(i["formula"].startswith("#5") for i in bread))   # under 3: no round-up
        self.assertTrue(all(i["question"].endswith("?") for i in bread))

    def test_numbering_stripped_and_plurals_folded(self):
        self.assertEqual(questions.clean("1. How do you fix dense bread?"),
                         "How do you fix dense bread?")
        self.assertEqual(questions.stem("starters"), "starter")
        self.assertEqual(questions.stem("loaves"), "loave")      # light folding only
        self.assertEqual(questions.stem("glass"), "glass")

    def test_without_seed_the_seed_word_dominates(self):
        r = questions.cluster(questions.read(PASTED))
        self.assertEqual(r["clusters"][0]["topic"], "sourdough")

    def test_empty(self):
        self.assertIsNone(questions.cluster(questions.read("")))
        self.assertIsNone(questions.cluster(questions.read("# only a source line\n")))

    def test_cli(self):
        p = run_cli("tt-seo", "questions.py", "-", "--seed", "sourdough", "--json", stdin=PASTED)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        self.assertEqual(json.loads(p.stdout.decode("utf-8"))["clusters"][0]["topic"], "starter")
        self.assertEqual(run_cli("tt-seo", "questions.py", "-", stdin="\n").returncode, 2)


if __name__ == "__main__":
    unittest.main()
