# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
import json
import unittest

from helpers import load, run_cli

kwmap = load("tt-seo", "kwmap")

PASTED = ("# search suggestions: sourdough\n"
          "sourdough starter\n"
          "sourdough starter for beginners\n"
          "how to make sourdough starter\n"
          "# others searched for\n"
          "Sourdough Starter\n"
          "sourdough discard recipes\n"
          "1. sourdough discard recipes 12.5K posts\n")


class KwmapTest(unittest.TestCase):
    def test_primary_secondary_longtail_questions(self):
        m = kwmap.build(kwmap.read(PASTED), seed="sourdough")
        self.assertEqual(m["primary"]["phrase"], "sourdough starter")
        self.assertEqual(m["primary"]["sources"],
                         ["others searched for", "search suggestions: sourdough"])
        self.assertIn("sourdough discard recipes", [e["phrase"] for e in m["secondary"]])
        self.assertEqual([e["phrase"] for e in m["long_tail"]], ["sourdough starter for beginners"])
        self.assertEqual([e["phrase"] for e in m["questions"]], ["how to make sourdough starter"])
        self.assertEqual(m["hashtags"][0], "#sourdoughstarter")
        self.assertEqual(m["placement"]["caption_first_line"], "sourdough starter")

    def test_clean_keeps_numbers_that_are_part_of_the_phrase(self):
        self.assertEqual(kwmap.clean("10 minute meals"), "10 minute meals")
        self.assertEqual(kwmap.clean("iphone 15 tips"), "iphone 15 tips")
        self.assertEqual(kwmap.clean("2. iphone 15"), "iphone 15")
        self.assertEqual(kwmap.clean("- #breadtok 3M views"), "breadtok")

    def test_csv_with_volume_column_and_bom(self):
        text = "﻿Keyword,Popularity\r\nbread recipe,12K\r\nsourdough,40K\r\n"
        m = kwmap.build(kwmap.read(text))
        self.assertEqual(m["primary"]["phrase"], "sourdough")
        self.assertEqual(m["primary"]["volume"], 40000)

    def test_unicode_phrases(self):
        m = kwmap.build(kwmap.read("pão de queijo\npão de queijo receita\n"))
        self.assertEqual(m["primary"]["phrase"], "pão de queijo")
        self.assertIn("#pãodequeijo", m["hashtags"])

    def test_empty(self):
        self.assertIsNone(kwmap.build(kwmap.read("")))
        self.assertIsNone(kwmap.build(kwmap.read("# only a header\n")))

    def test_cli(self):
        p = run_cli("tt-seo", "kwmap.py", "-", "--json", stdin=PASTED)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        self.assertEqual(json.loads(p.stdout.decode("utf-8"))["primary"]["phrase"],
                         "sourdough starter")
        self.assertEqual(run_cli("tt-seo", "kwmap.py", "-", stdin="").returncode, 2)


if __name__ == "__main__":
    unittest.main()
