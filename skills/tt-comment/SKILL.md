---
name: tt-comment
description: >-
  Draft replies to comments on the user's own TikToks, pasted in by the user,
  plus reply-with-video ideas for the comments worth a whole video. Use when
  the user pastes TikTok comments and wants replies, or asks which TikTok
  comments to answer with a video. Every reply is a draft the user approves
  and posts by hand, one at a time.
license: MIT
metadata:
  maintainer: Ian Ryan Kirk
---

# tt-comment

The comments under a TikTok are the cheapest source of the next video and the
easiest place to sound like a bot. This skill drafts. The user posts.

## Input

The user pastes the comments, with the video they are under. Do not open
TikTok, do not use a browser tool, and do not ask for login details.

## Sort first

Put each comment in one bucket, then reply in this order:

| bucket | what it is | what to do |
| --- | --- | --- |
| **question** | asks something the video did not answer | short answer, or a video reply |
| **pushback** | disagrees, with or without a reason | concede what is right, then the specific point |
| **story** | the commenter shares their own version | react to the detail they gave |
| **praise** | thanks, compliments | a short, specific line, or a like by the user |
| **noise** | emoji, tags of friends, off-topic | usually no reply |
| **risk** | abuse, personal data, medical or legal crisis, minors | do not draft a jokey reply. Flag it for the user to handle |

## Reply drafts

- **One or two sentences.** Comment threads are read fast.
- **Answer the specific thing they said.** If a reply could sit under any
  comment, rewrite it.
- **No pitch, no link drops**, no "check my bio" unless the commenter asked
  where to find something.
- **Never invent facts** about the user, their results or their product. If the
  answer needs a fact you do not have, write `{{answer}}` and flag it.
- **Do not argue with bad faith.** Offer "no reply" as an option.
- Run every draft through `/tt-human`. Short text makes stock phrases louder.

## Video-reply ideas

TikTok lets creators reply to a comment with a video, and the comment shows
on screen. Pick up to three comments that:

1. ask a question other viewers are clearly also asking (repeats, likes on the
   comment), or
2. push back with a point worth showing rather than saying.

For each, give: the comment, a three-layer hook for `/tt-hook` (formula #12,
Comment Reply, is the usual fit), and one line on what to show.

## Output

```
REPLIES  (video: "3 screws shelf")

1. [question] @user: "does this work on plaster walls?"
   draft: Not with these screws. Plaster needs {{anchor type}}, I'll test it on camera.
   -> video reply idea (see below)

2. [pushback] @user: "8 screws is safer"
   draft: For a heavier load, yes. At 40 kilos the stud does the work, not the count.

3. [noise] @user: "😂😂"
   no reply suggested

VIDEO REPLY IDEAS
  1. "does this work on plaster walls?" -> hook: "Plaster wall, same shelf, same
     40 kilos. Let's see." / on screen: PLASTER TEST / visual: shelf already loaded
```

## Never

Nothing is posted, liked, pinned, deleted or reported by this skill. There is
no auto-reply and no batch posting. The user reads each draft, edits it, and
posts it by hand, one at a time.
