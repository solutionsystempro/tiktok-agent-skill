# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
"""Consistency checks: manifests parse, versions agree, the README lists
exactly the skills that exist, headers and attribution are in place."""

import csv
import io
import json
import os
import re
import unittest

from helpers import ROOT, SKILLS

WORDS = {11: "Eleven", 12: "Twelve"}
ADAPTED = {"hookscore.py", "beats.py", "caption.py", "swipe.py", "retention.py",
           "humanize.py", "detect.py"}
ADAPTED_HEADER = ("# Adapted from instagram-agent-skill (c) 2026 Jake Schincariol. "
                  "Modifications (c) 2026 Ian Ryan Kirk. MIT License.")
NEW_HEADER = "# Copyright (c) 2026 Ian Ryan Kirk. MIT License."


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def skill_dirs():
    return sorted(d for d in os.listdir(SKILLS)
                  if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md")))


def prose_files():
    paths = [os.path.join(ROOT, "README.md"), os.path.join(ROOT, "CHANGELOG.md"),
             os.path.join(ROOT, "templates", "voice.md")]
    for d in skill_dirs():
        for f in os.listdir(os.path.join(SKILLS, d)):
            if f.endswith((".md", ".py")) or f in ("hooks.json", "rubric.json"):
                paths.append(os.path.join(SKILLS, d, f))
    return paths


class RepoTest(unittest.TestCase):
    def test_manifests(self):
        plugin = json.loads(read(".claude-plugin", "plugin.json"))
        market = json.loads(read(".claude-plugin", "marketplace.json"))
        entry = next(p for p in market["plugins"] if p["name"] == plugin["name"])
        self.assertEqual(plugin["version"], "1.0.0")
        self.assertEqual(entry["version"], plugin["version"])
        self.assertEqual(plugin["author"], {"name": "Ian Ryan Kirk",
                                            "url": "https://github.com/solutionsystempro"})
        for url in (plugin["homepage"], plugin["repository"], entry["homepage"]):
            self.assertEqual(url, "https://github.com/solutionsystempro/tiktok-agent-skill")
        count = WORDS[len(skill_dirs())]
        self.assertTrue(plugin["description"].startswith(count))
        self.assertTrue(entry["description"].startswith(count))

    def test_data_files_parse(self):
        for path in (("tt-hook", "hooks.json"), ("tt-human", "slop.json"),
                     ("tt-profile", "rubric.json")):
            json.loads(read("skills", *path))

    def test_rubric_totals_100(self):
        rubric = json.loads(read("skills", "tt-profile", "rubric.json"))
        self.assertEqual(sum(i["points"] for i in rubric["items"]), rubric["total"])
        self.assertEqual(rubric["total"], 100)

    def test_trends_template_matches_schema(self):
        head = next(csv.reader(io.StringIO(read("skills", "tt-trends", "trends.csv"))))
        for field in ("captured_at", "kind", "name", "rank", "views", "posts", "region",
                      "source", "url"):
            self.assertIn(field, head)
        schema = read("skills", "tt-trends", "schema.md")
        for field in head[:9]:
            self.assertIn(f"`{field}`", schema)

    def test_skill_frontmatter(self):
        for d in skill_dirs():
            front = read("skills", d, "SKILL.md").split("---")[1]
            self.assertRegex(front, rf"(?m)^name: {re.escape(d)}$")
            self.assertIn("TikTok", front, f"{d} description should name the platform")
            self.assertRegex(front, r"(?m)^license: MIT$")
            self.assertRegex(front, r"(?m)^  maintainer: Ian Ryan Kirk$")

    def test_skill_count_is_eleven_or_twelve(self):
        self.assertIn(len(skill_dirs()), WORDS)
        self.assertTrue(all(d.startswith("tt-") for d in skill_dirs()))

    def test_readme_lists_every_skill_and_no_others(self):
        readme = read("README.md")
        listed = set(re.findall(r"(?m)^\| `/(tt-[a-z]+)` \|", readme))
        self.assertEqual(listed, set(skill_dirs()))
        count = WORDS[len(skill_dirs())]
        self.assertIn(f"{count} Claude skills", readme)
        self.assertIn(f"The {count.lower()}", readme)
        self.assertIn("https://github.com/Jakeschincariol/instagram-agent-skill", readme)
        self.assertIn("Structure and several tools adapted from Jake Schincariol's", readme)

    def test_license_has_both_notices(self):
        lic = read("LICENSE")
        self.assertIn("Copyright (c) 2026 Ian Ryan Kirk", lic)
        self.assertIn("Portions derived from instagram-agent-skill, Copyright (c) 2026 "
                      "Jake Schincariol, MIT License", lic)
        self.assertEqual(lic.count("Permission is hereby granted"), 2)

    def test_python_headers(self):
        for d in skill_dirs():
            for f in os.listdir(os.path.join(SKILLS, d)):
                if not f.endswith(".py"):
                    continue
                second = read("skills", d, f).split("\n")[1]
                expected = ADAPTED_HEADER if f in ADAPTED else NEW_HEADER
                self.assertEqual(second, expected, f"{d}/{f}")

    def test_slop_json_carries_attribution(self):
        self.assertIn("Jake Schincariol", json.loads(read("skills", "tt-human", "slop.json"))["license"])

    def test_skill_docs_use_portable_tool_paths(self):
        for d in skill_dirs():
            text = read("skills", d, "SKILL.md")
            self.assertNotRegex(text, r"(?m)^python3 ")
            for tool in re.findall(r"(?m)^python \"([^\"]+)\"", text):
                self.assertTrue(tool.startswith("${CLAUDE_SKILL_DIR}/"), f"{d}: {tool}")
                name = tool.split("/", 1)[1]
                self.assertTrue(os.path.isfile(os.path.join(SKILLS, d, name)), f"{d}: {name}")

    def test_no_em_dashes_in_prose(self):
        # The humanizer's code and lexicon contain the character as data.
        for path in [p for p in prose_files() if not p.endswith(".py")]:
            with open(path, encoding="utf-8") as fh:
                self.assertNotIn("—", fh.read(), os.path.relpath(path, ROOT))

    def test_terms_citations_name_the_verified_section_and_version(self):
        # Verified against the US Terms of Service page, last updated July 15,
        # 2026: the scraping bullet is in section 3.4 and carries an "except
        # as approved in writing" exception.
        cited = 0
        for path in prose_files():
            if path.endswith(".py"):
                continue
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            if "terms-of-service" not in text:
                continue
            cited += 1
            rel = os.path.relpath(path, ROOT)
            self.assertIn("section 3.4", text, rel)
            self.assertIn("July 15, 2026", text, rel)
            self.assertNotIn("automated scripts to collect", text, rel)
            self.assertNotRegex(text, r"(?i)section 5\b", rel)
        self.assertGreaterEqual(cited, 5)

    def test_no_scraping_tools_recommended(self):
        banned = re.compile(r"(?i)apify|scrapecreators|playwright|selenium|puppeteer|yt-dlp")
        for path in prose_files():
            if path.endswith(".py"):
                continue
            with open(path, encoding="utf-8") as fh:
                self.assertNotRegex(fh.read(), banned, os.path.relpath(path, ROOT))


if __name__ == "__main__":
    unittest.main()
