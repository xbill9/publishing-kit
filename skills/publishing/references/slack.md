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

## Driving the composer, if you do it in a browser

MEASURED 2026-09-01 in that channel.

Unlike Medium and LinkedIn, **the Slack composer is not in a shadow root**. It is
a Quill editor reachable directly: `document.querySelector('[data-qa="texty_input"]')`,
`class="ql-editor"` (plus `ql-blank` while empty). So the usual bridge is not
needed — click it, assert it is empty, and `document.execCommand("insertText",
false, text)`.

**Never type into it.** Enter sends. There is no draft state to recover from and
no undo the other members will not have already seen, so every keystroke into a
focused Slack composer is one keypress away from posting. `insertText` in one
call is the only safe way in.

### A trailing `#hashtag` leaves the channel picker open

In Slack `#` opens the channel autocomplete, so the post's final line
(`#ClaudeCode #DevRel #Publishing #AWS`) left a channel list floating over the
composer, with `Enter` bound to **insert `#aws-reinvent` as a channel link**
rather than to send.

**Press Escape before handing the composer back.** Verified it closes the picker
and leaves the text untouched — 1302 characters before and after, all four links
still present exactly once.

The hashtags themselves are fine: as long as no suggestion is accepted they post
as plain text, which is what the author's earlier posts in the channel show.

## What the posted message actually looked like

MEASURED 2026-09-01, reading the sent message back out of the channel.

The Escape held: **no channel link was inserted anywhere.** The trailing
`#ClaudeCode #DevRel #Publishing #AWS` posted as plain text, all four
destination links appear exactly once, the GDE dev.to copy is absent, and the
message renders as four labelled blue links under three lines of prose.

Two details worth knowing before writing the next one:

- **The label "Dev.to" is auto-linked too.** Slack linkifies anything that looks
  like a hostname, so in `Dev.to is here:` the *word* becomes a link to dev.to's
  homepage, sitting immediately above the real article link. Harmless, and the
  author's own format has always read that way — but it is why that one line has
  two links in it and the others have one.
- **No unfurl cards appeared.** The previous post in the channel had a preview
  card; this one, several minutes after sending, had none for any of the four
  URLs. Whether that is the domains, the workspace, or just timing is not
  established — do not promise an author that their links will preview.
