# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
import os
import tempfile
import unittest

from helpers import load, run_cli, temp_file

swipe = load("tt-viral", "swipe")

TSV = (
    "﻿account\tfollowers\tmedian\tviews\thook\r\n"
    "@a\t48K\t11,000\t412K\tThe mistake that makes your bread dense every time\r\n"
    "@b\t2M\t900000\t1.2M\tin this video I am going to show you my morning routine \U0001F525\r\n"
    "@c\t4000\t3000\t180000\tPOV: your starter finally doubled\r\n"
)


def rows_of(text):
    return swipe.read_rows(text)[0]


class ParseCountTest(unittest.TestCase):
    def test_short_forms(self):
        self.assertEqual(swipe.parse_count("412K"), 412_000)
        self.assertEqual(swipe.parse_count("1.2M"), 1_200_000)
        self.assertEqual(swipe.parse_count("1,2M"), 1_200_000)
        self.assertEqual(swipe.parse_count("12.5k views"), 12_500)
        self.assertEqual(swipe.parse_count("412,000"), 412_000)
        self.assertEqual(swipe.parse_count("1,234,567"), 1_234_567)

    def test_malformed_is_none_not_a_guess(self):
        for bad in ("", None, "lots", "1.2.3M", "12,34", "K", "-5"):
            self.assertIsNone(swipe.parse_count(bad), bad)


BREAKDOWN_TSV = (
    "creator\tmedian\tviews\thook\ttype\ttopic\tlength\tstructure\tcta\n"
    "@a\t1000\t20000\tPOV: your starter doubled\t\tstarter\t0:21\tStory\tfollow\n"
    "@b\t1000\t15000\tRanking every flour\tranking\tflour\t34s\tlist\tcomment keyword\n"
    "@c\t1000\t9000\tEveryone says rinse rice\tmyth\trice\t40\tmyth-bust\tnone\n"
    "@d\t1000\t8000\tMy landlord just texted\t\tstarter\t25\tstory\tfollow\n"
    "@e\t1000\t3000\tLook at this bread\t\tbread\t60\ttutorial\tnone\n"
    "@f\t1000\t2000\tHere is my bread\t\tbread\tabout a minute\ttutorial\tnone\n"
    "@g\t1000\t1500\tToday we bake\t\tbread\t55\ttutorial\tfollow\n"
    "@h\t1000\t1000\tBaking again\t\tstarter\t50\tlist\tnone\n"
)


class BreakdownTest(unittest.TestCase):
    def setUp(self):
        rows, self.problems = swipe.read_rows(BREAKDOWN_TSV)
        self.a = swipe.analyse(rows, swipe.load_formulas(swipe.HOOKS))
        self.b = self.a["breakdown"]

    def test_aliases_and_length_parsing(self):
        first = self.a["videos"][0]
        self.assertEqual(first["account"], "@a")
        self.assertEqual(first["length_s"], 21.0)
        self.assertEqual(first["structure"], "story")             # case folded
        self.assertTrue(any("about a minute" in p for p in self.problems))

    def test_top_quartile_and_most_common(self):
        self.assertEqual(self.b["posts"], 8)
        self.assertEqual(self.b["top_quartile_size"], 2)
        structure = self.b["fields"]["structure"]
        self.assertEqual(structure["most_common"][0], ("tutorial", 3))
        self.assertEqual(dict(structure["top_quartile"]), {"story": 1, "list": 1})

    def test_blank_hook_type_falls_back_to_formula(self):
        hook_types = dict(self.b["fields"]["hook_type"]["most_common"])
        self.assertEqual(hook_types.get("point of view"), 1)
        self.assertEqual(hook_types.get("ranking"), 1)

    def test_stands_out_needs_two_top_posts_and_a_higher_share(self):
        # top two are @a (starter, follow) and @b (flour, comment keyword): nothing
        # appears twice in the top quartile, so nothing stands out.
        for f in self.b["fields"].values():
            self.assertEqual(f["stands_out"], [])
        rows, _ = swipe.read_rows(BREAKDOWN_TSV.replace("comment keyword", "follow")
                                  .replace("\tflour\t", "\tstarter\t"))
        b = swipe.analyse(rows, None)["breakdown"]
        cta = b["fields"]["cta"]["stands_out"]
        self.assertEqual([s["value"] for s in cta], ["follow"])
        self.assertEqual(cta[0]["top_share"], 1.0)
        self.assertEqual(cta[0]["all_share"], round(4 / 8, 2))

    def test_median_lengths(self):
        self.assertEqual(self.b["median_length_s"], 40.0)        # 21,34,40,25,60,55,50
        self.assertEqual(self.b["top_quartile_median_length_s"], 27.5)

    def test_empty_breakdown_fields(self):
        b = swipe.analyse(swipe.read_rows("views\thook\n5000\tone\n")[0], None)["breakdown"]
        self.assertEqual(b["fields"]["topic"]["filled"], 0)
        self.assertIsNone(b["median_length_s"])
        self.assertEqual(b["top_quartile_size"], 0)

    def test_markdown_includes_breakdown(self):
        md = swipe.to_markdown(self.a)
        self.assertIn("## Breakdown", md)
        self.assertIn("structure (8 filled): tutorial x3", md)


class ParseSecondsTest(unittest.TestCase):
    def test_fractions_are_kept(self):
        self.assertEqual(swipe.parse_seconds("1:02.5"), 62.5)
        self.assertEqual(swipe.parse_seconds("0:34"), 34.0)
        self.assertEqual(swipe.parse_seconds("1:02:03.25"), 3723.25)
        self.assertEqual(swipe.parse_seconds("34.5s"), 34.5)

    def test_bad_values(self):
        for bad in ("", None, "1:2:3:4", "1:75x", "a minute"):
            self.assertIsNone(swipe.parse_seconds(bad), bad)


class SwipeTest(unittest.TestCase):
    def test_ranks_by_multiple_not_views(self):
        a = swipe.analyse(rows_of(TSV), swipe.load_formulas(swipe.HOOKS))
        self.assertEqual([r["account"] for r in a["videos"]], ["@c", "@a", "@b"])
        self.assertEqual(a["videos"][0]["outlier"], 60.0)
        self.assertEqual(a["videos"][0]["formula"], "Point of View")
        self.assertEqual(a["videos"][1]["formula"], "Mistake Count")
        self.assertEqual(a["baseline"], "account median")
        self.assertIsNotNone(a["videos"][0]["hook_score"])

    def test_mixed_baselines_are_labelled_per_row(self):
        text = ("account,followers,median,views,hook\n"
                "@a,48000,11000,412000,one\n"
                "@b,4000,,180000,two\n"
                "@c,9000,,90000,three\n")
        a = swipe.analyse(rows_of(text), None)
        self.assertEqual(a["baseline"], "mixed (1 account median, 2 follower count)")
        by = {r["account"]: r for r in a["videos"]}
        self.assertEqual(by["@a"]["baseline_source"], "median")
        self.assertEqual(by["@b"]["baseline_source"], "followers")
        self.assertEqual(by["@b"]["outlier"], 45.0)
        md = swipe.to_markdown(a)
        self.assertIn("baseline: 4,000 (follower count)", md)
        self.assertIn("baseline: 11,000 (account median)", md)

    def test_csv_with_quoted_commas_in_hook(self):
        text = 'account,median,views,hook\n@a,1000,5000,"Wait, this is what 200 days looks like"\n'
        rows = rows_of(text)
        self.assertEqual(rows[0]["hook"], "Wait, this is what 200 days looks like")

    def test_malformed_counts_are_reported(self):
        rows, problems = swipe.read_rows("account\tfollowers\tviews\thook\n"
                                         "@a\tmany\t5000\tone\n@b\t100\tlots\ttwo\n")
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["followers"])
        self.assertEqual(len(problems), 2)

    def test_no_baseline_at_all(self):
        a = swipe.analyse(rows_of("views\thook\n5000\tone\n"), None)
        self.assertIsNone(a["videos"][0]["outlier"])
        self.assertEqual(a["baseline"], "none")

    def test_header_without_views_or_hook_is_an_error(self):
        with self.assertRaises(ValueError):
            swipe.read_rows("account\tfollowers\n@a\t100\n")

    def test_empty(self):
        self.assertEqual(swipe.read_rows(""), ([], []))

    def test_missing_hooks_file_degrades(self):
        a = swipe.analyse(rows_of(TSV), swipe.load_formulas("no/such/file.json"))
        self.assertEqual(a["unclassified"], 3)

    def test_cli_writes_markdown_and_handles_emoji(self):
        path = temp_file(TSV, suffix=".tsv")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                p = run_cli("tt-viral", "swipe.py", path, "--out", "swipe.md", cwd=tmp)
                self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
                with open(os.path.join(tmp, "swipe.md"), encoding="utf-8") as fh:
                    self.assertIn("# TikTok swipe file", fh.read())
                self.assertIn("\U0001F525", p.stdout.decode("utf-8"))
        finally:
            os.remove(path)

    def test_cli_no_rows_exits_2(self):
        p = run_cli("tt-viral", "swipe.py", "-", stdin="views\thook\nlots\tx\n")
        self.assertEqual(p.returncode, 2)


if __name__ == "__main__":
    unittest.main()
