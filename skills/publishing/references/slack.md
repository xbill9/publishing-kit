# AWS Community Builders Slack, measured

**Optional, and after the fact.** Announcing a published article in a community
channel. Nothing else in the kit calls `make-slack.py`.

Measured 2026-09-01 in `AWS Builder Community`, `#boost-ai-engineering`
(`app.slack.com/client/E08R531Q42K/C08B56GB1RT`).

## The format is the author's own, read out of the channel

Taken from the previous post in that channel rather than invented:

```
<two or three lines of plain context: the problem, the alternative,
 what you actually did>
Builder Center Article is here:
<link>
Medium is here:
<link>
Dev.to is here:
<link>
Linked In is here:
<link>
#JAX #Gravitron #Gemma4 #CUDA #arm
```

Three things about it are load-bearing:

- **The order is Builder Center, Medium, Dev.to, LinkedIn.** Not alphabetical,
  not the order the kit builds them.
- **The dev.to link is the `aws-builders` one, not the GDE copy.** It is an AWS
  community channel. `make-slack.py` fails if the two are the same URL.
- **The context lines are prose, not a summary of the piece.** The existing post
  opens with the problem and what was done, then lets the links carry the rest.

The shape lives in `templates/slack-post.txt`.

## Slack is not markdown

The composer is WYSIWYG with its own toolbar (bold, italic, underline, strike,
link, lists, code, code block). Slack's markup is mrkdwn — `*bold*` with single
asterisks, `_italic_`, `<url|label>` — so markdown `**bold**` arrives as literal
asterisks and `[label](url)` as literal brackets.

`make-slack.py` strips markdown rather than translating it, because the author's
existing posts put a bare URL on its own line and let Slack unfurl it. That also
means a labelled link is not available without hand-editing in the composer.

## The script does not post

It writes a file. A shared channel had 656 members when this was measured, and
there is no edit that the ones who already read it will see. Paste it yourself.
