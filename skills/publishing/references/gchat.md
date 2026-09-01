# GDE Americas (Google Chat), and what is not yet measured

**Optional, and after the fact.** Announcing a published article in the GDE
Americas space. Nothing else in the kit calls `make-gchat.py`.

## It is the Slack post with the other community's copy

The shape is deliberately the author's Slack format: a few lines of plain
context, then one labelled link per destination, each URL on its own line for
the client to unfurl. A reader in either community sees something familiar.

The one thing that must differ is which copy of the article they get:

| Room | dev.to link |
| --- | --- |
| `#boost-ai-engineering` (AWS Builder Community, Slack) | `dev.to/aws-builders` |
| GDE Americas (Google Chat) | `dev.to/gde` |

`make-gchat.py` fails when the GDE link is the aws-builders one — the mirror of
the check in `make-slack.py`, and verified by feeding it a swapped `links.txt`
rather than by trusting that it would fire.

The link **order** flips too, for the same reason: lead with the copy that
belongs to the room. Slack gets Builder Center first; the GDE space gets dev.to
first. The shape lives in `templates/gchat-post.txt`.

## Markup

Chat's markup is `*bold*`, `_italic_`, `~strike~`, `` `code` `` — close enough
to Slack's mrkdwn that markdown `**bold**` and `[label](url)` are wrong in both.
The script strips markdown rather than translating it, exactly as the Slack one
does, and the check for leftovers is the same.

## What is deliberately NOT claimed here

This file is short because nobody has yet driven the GDE Americas space. This
kit's rule is that a destination's behaviour is measured or it is not written
down, and the Slack file next door earned every line of itself by being wrong
first. So the following are **open questions, not documented behaviour**:

- whether a `#hashtag` does anything (in Slack it opens the channel picker and
  leaves Enter bound to inserting a channel link — see `slack.md`)
- what the composer is built from, and whether it is reachable in the main
  document or behind a shadow root
- whether Enter sends

`--hashtags` is therefore empty unless passed, and the safe assumptions until
someone measures are the Slack ones: **assume Enter sends, and paste rather than
type.**

## The script does not post

It writes a file. Sending into a shared community space is a person's decision.
