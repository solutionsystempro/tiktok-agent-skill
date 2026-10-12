# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
import json
import os
import unittest

from helpers import load, run_cli, temp_file

beats = load("tt-script", "beats")

SCRIPT = ("This shelf holds 40 kilos with three screws.\n"
          "[B-roll: drilling]\n"
          "First screw goes into the stud, not the drywall.\n"
          "That is the whole trick. Three screws, forty kilos.\n")


class BeatsTest(unittest.TestCase):
    def test_labels_loop_and_directions(self):
        a = beats.analyse(SCRIPT, wpm=165, target=12)
        self.assertEqual(len(a["beats"]), 3)
        self.assertEqual(a["beats"][0]["label"], "HOOK")
        self.assertEqual(a["beats"][-1]["label"], "CTA")
        self.assertEqual(a["beats"][1]["directions"], ["B-roll: drilling"])
        self.assertTrue(any(n.startswith("Loops:") for n in a["notes"]))

    def test_directions_take_no_time(self):
        with_dir = beats.analyse(SCRIPT)
        without = beats.analyse(SCRIPT.replace("[B-roll: drilling]\n", ""))
        self.assertEqual(with_dir["total_seconds"], without["total_seconds"])

    def test_hook_beat_over_three_seconds_is_flagged(self):
        a = beats.analyse(" ".join(["word"] * 12) + "\nshort end.\n", wpm=165)
        self.assertTrue(a["beats"][0]["flags"])
        self.assertTrue(any(n.startswith("Hook beat takes") for n in a["notes"]))

    def test_short_hook_is_not_flagged(self):
        a = beats.analyse("Three screws, forty kilos.\nThat is it.\n")
        self.assertFalse(a["beats"][0]["flags"])

    def test_total_against_target(self):
        over = beats.analyse(" ".join(["word"] * 165) + "\n", wpm=165, target=30)
        self.assertTrue(any("over target" in n for n in over["notes"]))
        under = beats.analyse("One two three four.\n", target=30)
        self.assertTrue(any("under target" in n for n in under["notes"]))

    def test_wpm_changes_timing(self):
        slow = beats.analyse(SCRIPT, wpm=120)["total_seconds"]
        fast = beats.analyse(SCRIPT, wpm=200)["total_seconds"]
        self.assertGreater(slow, fast)

    def test_crlf_and_bom(self):
        a = beats.analyse("﻿" + SCRIPT.replace("\n", "\r\n"))
        self.assertEqual(len(a["beats"]), 3)
        self.assertFalse(a["beats"][0]["text"].startswith("﻿"))

    def test_empty_and_directions_only(self):
        self.assertIsNone(beats.analyse("\n  \n"))
        self.assertIsNone(beats.analyse("[TEXT: only a card]\n"))

    def test_timecode_rolls_over(self):
        self.assertEqual(beats.tc(59.96), "1:00.0")

    def test_cli_bad_wpm_and_target(self):
        path = temp_file(SCRIPT)
        try:
            self.assertEqual(run_cli("tt-script", "beats.py", path, "--wpm", "0").returncode, 2)
            self.assertEqual(run_cli("tt-script", "beats.py", path, "--wpm", "nan").returncode, 2)
            self.assertEqual(run_cli("tt-script", "beats.py", path, "--target", "-5").returncode, 2)
        finally:
            os.remove(path)

    def test_cli_json_with_emoji(self):
        p = run_cli("tt-script", "beats.py", "-", "--json",
                    stdin="Three screws \U0001F529 forty kilos.\nDone.\n")
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        self.assertIn("\U0001F529", json.loads(p.stdout.decode("utf-8"))["beats"][0]["text"])


if __name__ == "__main__":
    unittest.main()
