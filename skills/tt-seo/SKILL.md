---
name: tt-seo
description: >-
  TikTok search keyword and question research from what the user pastes:
  search suggestions, keyword lists and questions, turned into a keyword map
  by kwmap.py and question clusters with script ideas by questions.py. Use
  when the user wants TikTok SEO, TikTok search keywords, or wants to know what
  questions to answer in TikToks. No scraping.
license: MIT
metadata:
  maintainer: Ian Ryan Kirk
---

# tt-seo

People type questions into TikTok search. A video that says the phrase they
typed, shows it on screen and writes it in the caption gives search something
to match. This skill finds the phrase from what the user pastes and maps where
it goes.

```bash
python "${CLAUDE_SKILL_DIR}/kwmap.py" pasted.txt --seed "sourdough"
python "${CLAUDE_SKILL_DIR}/kwmap.py" keywords.csv --json
python "${CLAUDE_SKILL_DIR}/questions.py" questions.txt --seed "sourdough"
```

`${CLAUDE_SKILL_DIR}` is this skill's folder. On macOS or Linux, use `python3`
if `python` is not found.

## Where the phrases come from

Only from the user, by hand. This skill and its tool never fetch anything from
TikTok. Ask the user to collect:

1. **Search suggestions.** Type the topic into TikTok search slowly and copy
   the suggestions that appear. Repeat with two or three variations ("topic
   for beginners", "how to topic", "topic mistakes").
2. **"Others searched for" and related searches** shown on results and under
   videos, where the app shows them.
3. **TikTok Creative Center** keyword lists, if the user has access, copied by
   hand. Which keyword tools Creative Center shows, and to which accounts and
   regions, changes and is unverified here.
4. **Comments on the user's own videos** that ask a question. Those are
   searches waiting to happen.

Paste each list under a `# source name` line so phrases that appear in more
than one list rank higher:

```
# search suggestions: sourdough
sourdough starter
sourdough starter for beginners
# others searched for
sourdough discard recipes
```

## What comes back

- **Primary keyword**: the phrase to say in the hook, put on screen and use in
  caption line one.
- **Secondary**: two to five phrases for the caption body.
- **Long tail and questions**: each is a separate video idea. A question in
  search suggestions is a hook for `/tt-hook` (formula #5, The Typed
  Question).
- **Hashtags**: a few candidates built from the primary and secondary phrases.
  How many to use is a heuristic, see `/tt-caption`.

The ranking is from what was pasted (how many lists, how many mentions, how
many other phrases contain it), or from a volume column if the pasted table
has one. It is not TikTok search volume and the output says so.

## Question research

Questions are the most direct script ideas there are: someone already typed
the hook. Ask the user to paste questions about the topic from:

- TikTok search suggestions that are questions
- "People also ask" boxes in a web search
- Q&A sites and forum threads on the topic, read by hand
- comments under the user's own videos

One per line, with `# source` lines between lists, then:

```bash
python "${CLAUDE_SKILL_DIR}/questions.py" questions.txt --seed "sourdough"
```

It merges near-duplicates, clusters the rest by their most widely shared
topic word (the `--seed` words are ignored for this, or every question would
land in one cluster), and maps each cluster to script ideas: one video per
question (hook formula #5, The Typed Question) and, for clusters of three or
more, a round-up video (formula #6, Numbered Lessons). The clustering is word
overlap, not meaning, so read the clusters and move a question if it landed
in the wrong one.

Nothing is fetched. Every question comes from the user.

## Rules

- **No scraping, no unofficial APIs, no browser automation.** TikTok's US
  Terms of Service (version of July 15, 2026), section 3.4, prohibit using
  automated systems or software to scrape, crawl, export or extract data or
  content from the platform, except as approved in writing by TikTok:
  https://www.tiktok.com/legal/page/us/terms-of-service/en
- **Do not stuff.** One primary phrase said naturally beats five crammed into
  one caption.
- **Do not invent volume.** If the user asks "how many people search this",
  the honest answer is that pasted lists do not say.

Hand the map to `/tt-hook`, `/tt-script` and `/tt-caption`.
