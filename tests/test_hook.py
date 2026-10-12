# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
import json
import os
import re
import unittest

from helpers import SKILLS, load, run_cli, temp_file

hookscore = load("tt-hook", "hookscore")

STRONG = {
    "spoken": "This chair cost $1,400. Here is what it buys you.",
    "text": "$1,400 CHAIR. WORTH IT?",
    "visual": "Hand slaps the price sticker onto the chair.",
}
WEAK = {
    "spoken": "Hey guys, today I wanted to talk about chairs",
    "text": "Hey guys today I wanted to talk about chairs",
    "visual": "Me sitting at a desk looking at the camera",
}


class HookscoreTest(unittest.TestCase):
    def test_three_strong_layers_beat_three_weak_ones(self):
        strong, weak = hookscore.run(STRONG), hookscore.run(WEAK)
        self.assertEqual(strong["verdict"], "STRONG", strong)
        self.assertEqual(weak["verdict"], "WEAK")
        self.assertGreater(strong["score"], weak["score"] + 50)
        self.assertTrue(any("Greeting" in f for f in weak["flags"]))
        self.assertTrue(any("Static opener" in f for f in weak["flags"]))

    def test_missing_layers_cost_points_and_block_strong(self):
        full = hookscore.run(STRONG)
        spoken_only = hookscore.run({"spoken": STRONG["spoken"]})
        self.assertEqual(spoken_only["missing"], ["ON-SCREEN", "VISUAL"])
        self.assertNotEqual(spoken_only["verdict"], "STRONG")
        self.assertLess(spoken_only["score"], full["score"])

    def test_onscreen_that_repeats_the_spoken_line_is_marked_down(self):
        _, checks, _ = hookscore.score_onscreen(WEAK["text"], WEAK["spoken"])
        self.assertEqual(checks["ADDS"][0], 40.0)

    def test_long_onscreen_text_fails_glance(self):
        _, checks, _ = hookscore.score_onscreen(" ".join(["word"] * 14))
        self.assertLess(checks["GLANCE"][0], 30)

    def test_emoji_only_card(self):
        _, checks, _ = hookscore.score_onscreen("\U0001F525\U0001F525")
        self.assertEqual(checks["GLANCE"][0], 20.0)

    def test_spoken_length_window_is_about_three_seconds(self):
        self.assertEqual(hookscore.check_length("one two three four five six")[0], 100.0)
        self.assertLess(hookscore.check_length(" ".join(["word"] * 14))[0], 50)

    def test_sentence_start_is_not_a_proper_noun(self):
        _, detail = hookscore.check_specificity("Bread. Here is the fix.")
        self.assertNotIn("Here", detail)

    def test_empty_hook(self):
        r = hookscore.run({})
        self.assertEqual(r["verdict"], "WEAK")
        self.assertEqual(r["score"], 0.0)

    def test_parse_blocks_bom_and_crlf(self):
        raw = ("﻿spoken: line one\r\ntext: CARD\r\nvisual: hand grabs it\r\n\r\n"
               "On-screen: SECOND\r\nframe: pours it\r\n")
        hooks = hookscore.parse(raw)
        self.assertEqual(hooks, [
            {"spoken": "line one", "text": "CARD", "visual": "hand grabs it"},
            {"text": "SECOND", "visual": "pours it"},
        ])

    def test_parse_plain_lines_are_spoken_only(self):
        self.assertEqual(hookscore.parse("one\n\ntwo\n"), [{"spoken": "one"}, {"spoken": "two"}])

    def test_cli_ranks_with_emoji_through_a_pipe(self):
        p = run_cli("tt-hook", "hookscore.py", "-",
                    stdin="Stop scrolling \U0001F525\nI lost $1,400 on one chair.\n")
        self.assertIn(p.returncode, (0, 1), p.stderr.decode("utf-8", "replace"))
        self.assertIn("HOOK RANKING", p.stdout.decode("utf-8"))

    def test_cli_flags_and_json(self):
        p = run_cli("tt-hook", "hookscore.py", "--spoken", STRONG["spoken"],
                    "--text", STRONG["text"], "--visual", STRONG["visual"], "--json")
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        self.assertEqual(json.loads(p.stdout.decode("utf-8"))["verdict"], "STRONG")

    def test_cli_empty_input_exits_2(self):
        self.assertEqual(run_cli("tt-hook", "hookscore.py", "-", stdin="").returncode, 2)

    def test_cli_reads_a_file_with_bom(self):
        path = temp_file("﻿spoken: My landlord just texted me this.\n")
        try:
            p = run_cli("tt-hook", "hookscore.py", path)
            self.assertIn("My landlord", p.stdout.decode("utf-8"))
            self.assertNotIn("﻿", p.stdout.decode("utf-8"))
        finally:
            os.remove(path)


class HooksJsonTest(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(SKILLS, "tt-hook", "hooks.json"), encoding="utf-8") as fh:
            self.data = json.load(fh)

    def test_twenty_formulas_with_three_layers(self):
        hooks = self.data["hooks"]
        self.assertEqual(len(hooks), 20)
        for h in hooks:
            for key in ("name", "template", "example", "on_screen", "first_visual",
                        "best_for", "trap", "match"):
                self.assertTrue(h.get(key), f"#{h['id']} missing {key}")

    def test_every_example_classifies_as_its_own_formula(self):
        by_id = {h["id"]: h for h in self.data["hooks"]}
        self.assertEqual(sorted(self.data["classify_order"]), sorted(by_id))
        for h in self.data["hooks"]:
            got = next((i for i in self.data["classify_order"]
                        if re.search(by_id[i]["match"], h["example"], re.IGNORECASE)), None)
            self.assertEqual(got, h["id"], f"#{h['id']} example classified as {got}")


if __name__ == "__main__":
    unittest.main()
