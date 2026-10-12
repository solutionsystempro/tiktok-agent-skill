# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
import os
import unittest

from helpers import load, run_cli, temp_file

caption = load("tt-caption", "caption")

GOOD = ("Sourdough starter in 5 days, no fancy flour.\n\n"
        "Day 1 is flour and water. Comment STARTER and I will send the schedule.\n\n"
        "#sourdough #sourdoughstarter")


def check(result, name):
    return next(c for c in result["checks"] if c["check"] == name)


class CaptionTest(unittest.TestCase):
    def test_clean_caption_is_ready(self):
        a = caption.analyse(GOOD, keywords=["sourdough starter"])
        self.assertEqual(a["verdict"], "READY", a["checks"])
        self.assertEqual(a["hashtags"], ["#sourdough", "#sourdoughstarter"])

    def test_limit_counts_utf16_units_not_characters(self):
        text = "a" * (caption.LIMIT - 10) + "\U0001F525" * 10   # 2,200 chars, 2,210 units
        a = caption.analyse(text)
        self.assertEqual(a["characters"], caption.LIMIT)
        self.assertEqual(a["utf16_units"], caption.LIMIT + 10)
        self.assertEqual(check(a, "LENGTH")["status"], "FAIL")

    def test_exactly_at_limit_is_not_a_fail(self):
        a = caption.analyse("a" * caption.LIMIT)
        self.assertNotEqual(check(a, "LENGTH")["status"], "FAIL")

    def test_bmp_text_counts_one_unit_each(self):
        self.assertEqual(caption.utf16_len("café 日本"), 7)

    def test_emoji_graphemes(self):
        # thumbs up + skin tone, heart + VS16, family ZWJ sequence, a flag: four emoji
        text = "Done \U0001F44D\U0001F3FD ❤️ \U0001F468‍\U0001F469‍\U0001F467 \U0001F1EF\U0001F1F5"
        self.assertEqual(caption.analyse(text)["emoji"], 4)

    def test_hashtag_guide_is_a_heuristic_warning_not_a_fail(self):
        tags = " ".join(f"#tag{i}" for i in range(caption.HASHTAG_GUIDE + 3))
        a = caption.analyse("Bread in 5 steps.\n\n" + tags)
        c = check(a, "HASHTAGS")
        self.assertEqual(c["status"], "WARN")
        self.assertIn("heuristic", c["detail"])

    def test_filler_tags_and_leading_tag(self):
        a = caption.analyse("#fyp bread in 5 steps #viral")
        self.assertEqual(check(a, "HASHTAGS")["status"], "WARN")
        self.assertEqual(check(a, "FIRST LINE")["status"], "FAIL")

    def test_unicode_hashtags(self):
        self.assertEqual(caption.analyse("Paris in 3 days.\n#café #日本")["hashtags"],
                         ["#café", "#日本"])

    def test_preview_stops_at_first_line_and_cut(self):
        a = caption.analyse("x" * 200 + "\nsecond line")
        self.assertEqual(len(a["visible"]), caption.TRUNCATE)
        self.assertTrue(a["truncated"])
        b = caption.analyse("Short first line.\nsecond line")
        self.assertEqual(b["visible"], "Short first line.")
        self.assertTrue(b["truncated"])

    def test_keywords_in_caption_window_and_cards(self):
        a = caption.analyse(GOOD, keywords=["sourdough starter", "rye bread"],
                            onscreen="STARTER IN 5 DAYS\nsourdough starter day one")
        self.assertEqual(check(a, "SEARCH TERMS")["status"], "WARN")
        self.assertIn("Missing: rye bread", check(a, "SEARCH TERMS")["detail"])
        self.assertEqual(check(a, "SEARCH ON SCREEN")["status"], "PASS")

    def test_long_card_warns(self):
        a = caption.analyse(GOOD, onscreen="one two three four five six seven eight nine ten")
        self.assertEqual(check(a, "CARD 1")["status"], "WARN")

    def test_leading_blank_line_is_caught(self):
        a = caption.analyse("\nActual caption with 3 steps.")
        self.assertEqual(check(a, "FIRST LINE")["status"], "FAIL")
        self.assertEqual(check(a, "FIRST LINE")["detail"], "the caption opens on a blank line")
        self.assertEqual(check(caption.analyse("﻿\r\nActual caption"), "FIRST LINE")["status"],
                         "FAIL")

    def test_empty_caption(self):
        a = caption.analyse("")
        self.assertEqual(a["verdict"], "FIX")
        self.assertEqual(check(a, "FIRST LINE")["detail"], "the caption is empty")

    def test_crlf_and_bom(self):
        a = caption.analyse("﻿ab\r\ncd")
        self.assertEqual(a["characters"], 5)
        self.assertEqual(a["visible"], "ab")

    def test_cli_emoji_pipe_and_bom_file(self):
        p = run_cli("tt-caption", "caption.py", "-", stdin="Bread \U0001F35E in 3 days.\n")
        self.assertIn(p.returncode, (0, 1), p.stderr.decode("utf-8", "replace"))
        self.assertIn("\U0001F35E", p.stdout.decode("utf-8"))
        path = temp_file("﻿" + GOOD)
        try:
            p = run_cli("tt-caption", "caption.py", path, "--keywords", "sourdough starter")
            self.assertEqual(p.returncode, 0, p.stdout.decode("utf-8", "replace"))
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
