# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
import json
import os
import unittest

from helpers import load, run_cli, temp_file

trends = load("tt-trends", "trends")

CSV = ("captured_at,kind,name,rank,posts,region\n"
       "2026-10-01,hashtag,#sourdoughtok,12,40000,US\n"
       "2026-10-01,hashtag,#breadfail,3,900000,US\n"
       "2026-10-08,hashtag,sourdoughtok,6,70000,US\n"
       "2026-10-08,hashtag,#breadfail,4,930000,US\n"
       "2026-10-08,sound,Kitchen beat,9,19000,US\n")


def rows(text, **kw):
    return trends.load(text, source="test", is_text=True, **kw)


def stage(g=None, rank=None, posts=None, age_days=30, **overrides):
    from datetime import date, timedelta
    t = dict(trends.THRESHOLDS, **overrides)
    latest = date(2026, 10, 8)
    return trends.stage_for(g, rank, posts, latest - timedelta(days=age_days), latest, t)


class VelocityTest(unittest.TestCase):
    def test_velocity_math_between_latest_two_snapshots(self):
        a = trends.analyse(rows(CSV))
        x = next(t for t in a["trends"] if t["name"] == "sourdoughtok")
        self.assertEqual(x["snapshots"], 2)                 # "#" ignored when matching
        self.assertEqual(x["first_seen"], "2026-10-01")
        self.assertEqual(x["rank_change_per_day"], round(6 / 7, 2))
        self.assertEqual(x["posts_per_day"], round(30000 / 7, 1))
        self.assertEqual(x["posts_growth_pct"], round(30000 / 40000 * 100 / 7, 2))
        self.assertEqual(x["stage"], "emerging")

    def test_three_snapshots_use_the_latest_pair(self):
        text = ("date,type,hashtag,posts\n2026-10-01,hashtag,a,100\n"
                "2026-10-05,hashtag,a,200\n2026-10-07,hashtag,a,210\n")
        x = trends.analyse(rows(text))["trends"][0]
        self.assertEqual(x["posts_per_day"], 5.0)
        self.assertEqual(x["posts_growth_pct"], 2.5)
        self.assertEqual(x["first_seen"], "2026-10-01")
        self.assertEqual(x["stage"], "peaking")

    def test_views_used_when_posts_missing(self):
        text = ("captured_at,kind,name,views\n2026-10-01,sound,s,1000\n2026-10-02,sound,s,900\n")
        x = trends.analyse(rows(text))["trends"][0]
        self.assertEqual(x["views_growth_pct"], -10.0)
        self.assertEqual(x["stage"], "fading")

    def test_single_snapshot_row(self):
        text = "captured_at,kind,name,rank\n2026-10-08,hashtag,lonely,3\n"
        x = trends.analyse(rows(text))["trends"][0]
        self.assertEqual(x["stage"], "one snapshot")
        self.assertEqual(x["velocity"], "one snapshot, no velocity")
        self.assertIsNone(x["rank_change_per_day"])

    def test_regions_are_separate_trends(self):
        text = ("captured_at,kind,name,posts,region\n2026-10-01,hashtag,a,100,US\n"
                "2026-10-08,hashtag,a,100,GB\n")
        a = trends.analyse(rows(text))
        self.assertEqual(len(a["trends"]), 2)
        self.assertTrue(all(t["stage"] == "one snapshot" for t in a["trends"]))


class StageTest(unittest.TestCase):
    def test_threshold_edges(self):
        t = trends.THRESHOLDS
        self.assertEqual(stage(t["rising_pct"]), "rising")
        self.assertEqual(stage(t["rising_pct"], age_days=t["emerging_days"]), "emerging")
        self.assertEqual(stage(t["rising_pct"], age_days=t["emerging_days"] + 1), "rising")
        self.assertEqual(stage(t["rising_pct"] - 0.01), "peaking")
        self.assertEqual(stage(t["peak_pct"]), "peaking")
        self.assertEqual(stage(t["peak_pct"] - 0.01), "stalled")
        self.assertEqual(stage(t["fading_pct"]), "stalled")
        self.assertEqual(stage(t["fading_pct"] - 0.01), "fading")

    def test_saturated_by_post_count(self):
        t = trends.THRESHOLDS
        self.assertEqual(stage(2.0, posts=t["saturated_posts"]), "saturated")
        self.assertEqual(stage(2.0, posts=t["saturated_posts"] - 1), "peaking")
        self.assertEqual(stage(t["rising_pct"], posts=t["saturated_posts"] * 5), "rising")

    def test_rank_only(self):
        self.assertEqual(stage(rank=1.0), "rising")
        self.assertEqual(stage(rank=1.0, age_days=2), "emerging")
        self.assertEqual(stage(rank=-1.0), "fading")
        self.assertEqual(stage(rank=0.5), "peaking")
        self.assertIsNone(stage())

    def test_falling_rank_with_flat_posts_is_fading(self):
        # Regression: rank 12 -> 30 in a week, posts 2000 -> 2100, views flat.
        text = ("captured_at,kind,name,rank,posts,views\n"
                "2026-10-01,sound,Slow song,12,2000,50000\n"
                "2026-10-08,sound,Slow song,30,2100,50000\n")
        x = trends.analyse(rows(text))["trends"][0]
        self.assertEqual(x["rank_change_per_day"], -2.57)
        self.assertEqual(x["posts_growth_pct"], round(5 / 7, 2))
        self.assertEqual(x["stage"], "fading")
        self.assertEqual(stage(0.7, rank=-2.57, posts=2100), "fading")
        self.assertEqual(stage(0.7, rank=-trends.THRESHOLDS["rank_rising"]), "fading")
        self.assertEqual(stage(0.7, rank=-0.5, posts=2100), "stalled")

    def test_falling_views_with_flat_posts_is_fading(self):
        self.assertEqual(trends.stage_for(0.5, None, 2100, *self._dates(),
                                          trends.THRESHOLDS, views_g=-3.0), "fading")

    def test_high_volume_flat_is_saturated(self):
        t = trends.THRESHOLDS
        self.assertEqual(stage(0.2, posts=t["saturated_posts"] * 2), "saturated")
        self.assertEqual(stage(0.0, rank=0.0, posts=t["saturated_posts"]), "saturated")

    def test_low_volume_flat_is_stalled(self):
        self.assertEqual(stage(0.2, posts=2100), "stalled")
        self.assertEqual(stage(0.0, posts=None), "stalled")
        text = ("captured_at,kind,name,posts\n2026-10-01,hashtag,quiet,2000\n"
                "2026-10-08,hashtag,quiet,2010\n")
        self.assertEqual(trends.analyse(rows(text))["trends"][0]["stage"], "stalled")

    @staticmethod
    def _dates():
        from datetime import date
        return date(2026, 9, 1), date(2026, 10, 8)

    def test_thresholds_are_configurable(self):
        self.assertEqual(stage(4.0), "peaking")
        self.assertEqual(stage(4.0, rising_pct=3.0), "rising")


class IngestTest(unittest.TestCase):
    def test_alias_mapping_semicolons_bom_crlf(self):
        text = ("﻿Snapshot Date;Type;Trend;Position;Video Count;Country\r\n"
                "2026/10/01;Hashtag;#bread;5;1.2K;us\r\n")
        r = rows(text)[0]
        self.assertEqual(r["captured_at"].isoformat(), "2026-10-01")
        self.assertEqual((r["kind"], r["name"], r["rank"], r["posts"], r["region"]),
                         ("hashtag", "#bread", 5, 1200, "US"))

    def test_kind_from_column_name_and_default_kind(self):
        r = rows("date,song,uses\n2026-10-01,Kitchen beat,20K\n")[0]
        self.assertEqual((r["kind"], r["name"], r["posts"]), ("sound", "Kitchen beat", 20000))
        r = rows("date,name\n2026-10-01,thing\n", default_kind="format")[0]
        self.assertEqual(r["kind"], "format")

    def test_json_shapes(self):
        flat = json.dumps([{"captured_at": "2026-10-01", "kind": "sound", "name": "s",
                            "posts": 10}])
        self.assertEqual(rows(flat)[0]["posts"], 10)
        snaps = json.dumps({"snapshots": [
            {"captured_at": "2026-10-01", "items": [{"kind": "hashtag", "name": "a", "posts": 100}]},
            {"captured_at": "2026-10-08T09:00:00Z",
             "items": [{"type": "hashtag", "trend": "a", "videos": "150"}]}]})
        a = trends.analyse(rows(snaps))
        self.assertEqual(a["trends"][0]["posts_per_day"], round(50 / 7, 1))

    def test_missing_required_column_is_a_clear_error(self):
        with self.assertRaises(ValueError) as ctx:
            rows("kind,name\nhashtag,a\n")
        self.assertIn("captured_at", str(ctx.exception))
        self.assertIn("\"kind\"", str(ctx.exception))
        with self.assertRaises(ValueError):
            rows("captured_at,name\n2026-10-01,a\n")       # no kind, no --kind

    def test_bad_rows_skipped_with_notes(self):
        notes = []
        r = trends.load("captured_at,kind,name\nnot a date,hashtag,a\n2026-10-01,meme,b\n"
                        "2026-10-01,hashtag,\n2026-10-01,hashtag,ok\n",
                        source="t", is_text=True, notes=notes)
        self.assertEqual([x["name"] for x in r], ["ok"])
        self.assertEqual(len(notes), 3)

    def test_empty_input(self):
        with self.assertRaises(ValueError):
            rows("")
        self.assertEqual(trends.analyse([])["trends"], [])


class NicheTest(unittest.TestCase):
    def test_fit_scores(self):
        self.assertEqual(trends.niche_fit("#sourdoughbread", ["sourdough bread"]), 100)
        self.assertEqual(trends.niche_fit("#breadtok", ["sourdough bread"]), 60)
        self.assertEqual(trends.niche_fit("#cats", ["sourdough"]), 0)
        self.assertIsNone(trends.niche_fit("#cats", []))

    def test_keywords_from_voice_md(self):
        path = temp_file("- **Niche keywords:** sourdough, bread (my main ones), baking\n")
        template = temp_file("- **Niche keywords:** (comma-separated, for example: a, b)\n")
        try:
            self.assertEqual(trends.niche_keywords_from_voice(path),
                             ["sourdough", "bread", "baking"])
            self.assertEqual(trends.niche_keywords_from_voice(template), [])
            self.assertEqual(trends.niche_keywords_from_voice("no/such/voice.md"), [])
        finally:
            os.remove(path)
            os.remove(template)

    def test_shortlist_prefers_fit_and_live_stages(self):
        a = trends.analyse(rows(CSV), keywords=["sourdough"])
        self.assertEqual([x["name"] for x in trends.shortlist(a)], ["sourdoughtok"])


class CliTest(unittest.TestCase):
    def test_outputs(self):
        path = temp_file(CSV, suffix=".csv")
        try:
            p = run_cli("tt-trends", "trends.py", path, "--niche", "sourdough,bread")
            out = p.stdout.decode("utf-8")
            self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
            self.assertIn("MAKE THIS WEEK", out)
            self.assertIn("rising >= 5.0%/day", out)
            self.assertIn("one snapshot, no velocity", out)
            p = run_cli("tt-trends", "trends.py", path, "--json", "--kind", "hashtag")
            data = json.loads(p.stdout.decode("utf-8"))
            self.assertEqual(list(data["by_kind"]), ["hashtag"])
            p = run_cli("tt-trends", "trends.py", path, "--markdown", "--top", "1")
            self.assertIn("## Make this week", p.stdout.decode("utf-8"))
        finally:
            os.remove(path)

    def test_errors_exit_2(self):
        empty = temp_file("", suffix=".csv")
        bad = temp_file("name\nx\n", suffix=".csv")
        try:
            self.assertEqual(run_cli("tt-trends", "trends.py", empty).returncode, 2)
            p = run_cli("tt-trends", "trends.py", bad)
            self.assertEqual(p.returncode, 2)
            self.assertIn("missing required column", p.stderr.decode("utf-8"))
        finally:
            os.remove(empty)
            os.remove(bad)


if __name__ == "__main__":
    unittest.main()
