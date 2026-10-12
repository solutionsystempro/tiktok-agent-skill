# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
import json
import os
import unittest

from helpers import load, run_cli, temp_file

retention = load("tt-retention", "retention")

CURVE = ("Time,Viewers (%)\n0,100\n1,92\n2,80\n3,71\n5,66\n8,60\n10,48\n15,40\n"
         "20,31\n25,22\n30,18\n")
SUMMARY = ("Video title,Video views,Average watch time,Watched full video (%),Duration\n"
           "Starter day 1,12.4K,6.2s,14.5%,22s\n"
           "Dense bread fix,48000,0:09.8,31.0%,18\n"
           "Oven spring test,3100,4.1,6.0,0:35\n")


class RetentionCurveTest(unittest.TestCase):
    def test_hook_leak_cliffs_and_crossings(self):
        a = retention.analyse_text(CURVE)
        self.assertEqual(a["mode"], "curve")
        self.assertEqual(a["hook_leak"], 29.0)
        self.assertEqual(a["below_50_at"], 10.0)
        self.assertEqual(a["below_25_at"], 25.0)
        steepest = max(a["cliffs"], key=lambda c: c["per_second"])
        self.assertEqual((steepest["from"], steepest["to"]), (1.0, 2.0))

    def test_ratio_header_and_flags(self):
        text = "second,audience retention ratio\n0,1.0\n2,0.8\n3,0.7\n6,0.5\n"
        a = retention.analyse_text(text)
        self.assertEqual(a["start"], 100.0)
        self.assertEqual(a["hook_leak"], 30.0)
        forced = retention.analyse_text("Time,Retention\n0,100\n3,60\n", force="percent")
        self.assertEqual(forced["hook_leak"], 40.0)

    def test_scale_guessed_from_values_says_so(self):
        a = retention.analyse_text("Time,Retention\n0,1\n3,0.5\n")
        self.assertEqual(a["hook_leak"], 50.0)
        self.assertTrue(any("guessed" in n for n in a["notes"]))

    def test_timecodes_reordered_columns_bom_crlf(self):
        text = "﻿Export for one video\r\nRetention (%),Time\r\n100,0:00\r\n70,0:03\r\n40,0:10\r\n"
        a = retention.analyse_text(text)
        self.assertEqual(a["hook_leak"], 30.0)
        self.assertEqual(a["length_seconds"], 10.0)

    def test_bad_rows_are_skipped_and_reported(self):
        a = retention.analyse_text("Time,Retention %\n0,100\nn/a,90\n3,70\n")
        self.assertEqual(a["points"], 2)
        self.assertTrue(any("skipped" in n for n in a["notes"]))


class RetentionSummaryTest(unittest.TestCase):
    def test_ranks_by_completion_with_mixed_time_formats(self):
        a = retention.analyse_text(SUMMARY)
        self.assertEqual(a["mode"], "summary")
        self.assertEqual(a["ranked_by"], "full")
        self.assertEqual([v["title"] for v in a["videos"]],
                         ["Dense bread fix", "Starter day 1", "Oven spring test"])
        self.assertEqual(a["median"], 14.5)
        dense = a["videos"][0]
        self.assertEqual(dense["avg_watch"], 9.8)
        self.assertEqual(dense["watch_share"], round(9.8 / 18 * 100, 1))
        self.assertEqual(a["videos"][2]["duration"], 35.0)

    def test_title_does_not_grab_the_views_column(self):
        a = retention.analyse_text("Video views,Average watch time\n100,5s\n200,7s\n")
        self.assertEqual(a["videos"][0]["title"], "row 2")
        self.assertEqual(a["ranked_by"], "avg_watch")


class RetentionErrorsTest(unittest.TestCase):
    def test_missing_columns_lists_headers(self):
        with self.assertRaises(ValueError) as ctx:
            retention.analyse_text("Account,Profile views\n@a,100\n")
        self.assertIn("\"Profile views\"", str(ctx.exception))
        self.assertIn("Average watch time", str(ctx.exception))

    def test_empty_file(self):
        with self.assertRaises(ValueError):
            retention.analyse_text("")

    def test_too_few_points(self):
        with self.assertRaises(ValueError):
            retention.analyse_text("Time,Retention\n0,100\n")

    def test_cli_error_exit_and_json(self):
        bad = temp_file("Account,Views\n@a,1\n", suffix=".csv")
        good = temp_file(CURVE, suffix=".csv", raw=("﻿" + CURVE).encode("utf-8"))
        try:
            p = run_cli("tt-retention", "retention.py", bad)
            self.assertEqual(p.returncode, 2)
            self.assertIn("could not recognise", p.stderr.decode("utf-8"))
            p = run_cli("tt-retention", "retention.py", good, "--json")
            self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
            self.assertEqual(json.loads(p.stdout.decode("utf-8"))["hook_leak"], 29.0)
            p = run_cli("tt-retention", "retention.py", "no/such/file.csv")
            self.assertEqual(p.returncode, 2)
        finally:
            os.remove(bad)
            os.remove(good)


if __name__ == "__main__":
    unittest.main()
