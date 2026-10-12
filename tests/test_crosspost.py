# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
import json
import unittest

from helpers import load, run_cli

crosspost = load("tt-caption", "crosspost")

GOOD = ("[tiktok]\nSourdough starter in 5 days. Comment STARTER.\n#sourdough\n"
        "[Shorts Title]\nSourdough starter in 5 days, no fancy flour\n"
        "[shorts description]\nDay 1 is flour and water.\n"
        "[reels]\nSourdough starter in 5 days.\n#sourdough #bread\n")


def statuses(r, key):
    return [c["status"] for c in r["platforms"][key]]


class CrosspostTest(unittest.TestCase):
    def test_clean_pack_is_ready(self):
        sections, unknown = crosspost.parse(GOOD)
        self.assertEqual(set(sections), set(crosspost.LABELS))
        self.assertEqual(unknown, [])
        self.assertEqual(crosspost.check(sections)["verdict"], "READY")

    def test_tiktok_counts_utf16_units(self):
        text = "a" * (crosspost.TIKTOK_UNITS - 1) + "\U0001F525"   # 2,200 chars, 2,201 units
        r = crosspost.check({"tiktok": text})
        self.assertIn("FAIL", statuses(r, "tiktok"))

    def test_shorts_title_limit_and_angle_brackets(self):
        self.assertIn("FAIL", statuses(crosspost.check({"shorts_title": "x" * 101}), "shorts_title"))
        self.assertNotIn("FAIL", statuses(crosspost.check({"shorts_title": "x" * 100}),
                                          "shorts_title"))
        self.assertIn("FAIL", statuses(crosspost.check({"shorts_title": "a <b>"}), "shorts_title"))

    def test_shorts_description_counts_bytes(self):
        text = "é" * 2501                        # 2,501 characters, 5,002 bytes
        r = crosspost.check({"shorts_description": text})
        self.assertIn("FAIL", statuses(r, "shorts_description"))
        self.assertIn("5002 / 5000 bytes", r["platforms"]["shorts_description"][-1]["detail"])

    def test_reels_hashtags_and_unverified_label(self):
        r = crosspost.check({"reels": "Bread.\n" + " ".join(f"#t{i}" for i in range(6))})
        details = " ".join(c["detail"] for c in r["platforms"]["reels"])
        self.assertIn("FAIL", statuses(r, "reels"))
        self.assertIn("unverified", details)

    def test_other_platform_mentions_warn(self):
        r = crosspost.check({"reels": "Full version on my TikTok"})
        self.assertIn("WARN", statuses(r, "reels"))

    def test_missing_and_empty_sections(self):
        sections, unknown = crosspost.parse("[tiktok]\n\n[pinterest]\nx\n")
        self.assertEqual(unknown, ["pinterest"])
        r = crosspost.check(sections)
        self.assertEqual(r["platforms"]["tiktok"][0]["detail"], "section is empty")
        self.assertEqual(r["platforms"]["reels"][0]["detail"], "section missing")
        self.assertEqual(r["verdict"], "FIX")

    def test_crlf_and_bom(self):
        sections, _ = crosspost.parse("﻿" + GOOD.replace("\n", "\r\n"))
        self.assertEqual(sections["shorts_title"], "Sourdough starter in 5 days, no fancy flour")

    def test_cli(self):
        p = run_cli("tt-caption", "crosspost.py", "-", "--json", stdin=GOOD)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        self.assertEqual(json.loads(p.stdout.decode("utf-8"))["verdict"], "READY")
        self.assertEqual(run_cli("tt-caption", "crosspost.py", "-", stdin="no headers").returncode, 2)


if __name__ == "__main__":
    unittest.main()
