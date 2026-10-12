---
name: tt-seo
description: >-
  TikTok search keyword research from phrases the user pastes: TikTok search
  suggestions, "others searched for", related searches and TikTok Creative
  Center keyword lists, turned into a keyword map by kwmap.py with where each
  phrase goes. Use when the user wants TikTok SEO, TikTok search keywords, or
  wants their TikToks found in TikTok search. No scraping.
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

## Rules

- **No scraping, no unofficial APIs, no browser automation.** TikTok's Terms of
  Service, section 3.4, prohibit scraping or extracting data from the platform:
  https://www.tiktok.com/legal/page/us/terms-of-service/en
- **Do not stuff.** One primary phrase said naturally beats five crammed into
  one caption.
- **Do not invent volume.** If the user asks "how many people search this",
  the honest answer is that pasted lists do not say.

Hand the map to `/tt-hook`, `/tt-script` and `/tt-caption`.
