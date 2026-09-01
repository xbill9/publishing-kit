# GDEs - Americas (Google Chat), measured

**Optional, and after the fact.** Announcing a published article in the GDE
Americas space (`chat.google.com/app/chat/AAAAiyul1_o`). Nothing else in the kit
calls `make-gchat.py`.

Everything below was measured in that space on 2026-09-01.

## The shape is this room's, not Slack's

Read out of the room rather than ported across from the Slack template. The two
communities write differently:

| | `#boost-ai-engineering` (Slack) | GDEs - Americas (Chat) |
| --- | --- | --- |
| opening | straight into the context | a line saying **why** you are posting |
| links | label on one line, URL on the next | `"... is here: <url>"`, inline |
| paragraphs | run together | separated by blank lines |
| hashtags | yes, the author's posts end in them | none, anywhere |

The author's own last post there opens *"Just posting in case this helps someone
out with…"* and closes *"My renewal post on LinkedIn is here: <url>"* on one
line. `templates/gchat-post.txt` is that shape. The lede is a template field:
rewrite it per article rather than shipping the default because it was there.

The dev.to link is the **`/gde/`** copy. Sending a Google community the AWS
org's copy is the same mistake as the reverse, and `make-gchat.py` fails on it —
verified by feeding it a swapped `links.txt` rather than trusting the check
would fire.

**The space is threaded.** Every top-level message becomes a topic with its own
reply count, so an announcement is a new conversation, not a line in a stream.

## `#` is a second mention trigger, and notify-all is first in the list

This is the one that would have gone wrong.

| typed, as real keystrokes | result |
| --- | --- |
| `@` | nothing |
| `#` | nothing |
| `@All` | **People picker opens** — `all / Notify all is limited in this space`, then members |
| `#ClaudeCode` | **the same picker opens** — People *and* Files |

So `#` is not inert in Google Chat the way it is in a document, and Enter with
that list open inserts whatever is highlighted. What is highlighted first is a
notify-everyone.

**The control is the whole point.** `@` alone opened nothing and `#` alone
opened nothing, which on its own reads as "hashtags are safe here". Both
triggers need a following letter. Testing only the thing that does not fire
would have produced exactly the wrong rule.

`make-gchat.py` therefore emits no hashtags and warns if you pass `--hashtags`.

## The composer

A single visible `[contenteditable="true"]`, `role="textbox"`, `aria-label`
"History is on". **No shadow root and no iframe** — unlike Medium and LinkedIn,
it is reachable straight from the document, like Slack's.

- **`execCommand("insertText")` puts the whole message in at once** and,
  usefully, does **not** open the pickers that real keystrokes do. Paste the
  message; do not type it.
- **Assume Enter sends.** Not tested, and not worth testing in a live space with
  a `Notify all` entry one keystroke away.
- **Escape closes a picker and leaves the text alone** — 1350 characters before
  and after, all four links intact. It does **not** clear the composer: text
  typed while probing survived it, and the insert's own emptiness guard is what
  caught the leftover `#ClaudeCode` before it shipped inside the post.
- **`innerText` reads back longer than what you inserted** (1350 vs 1343 here):
  blank-line paragraphs pick up extra newlines. Verify by counting links and
  reading the first line, not by comparing lengths for equality.

## The script does not post

It writes a file. Sending into a shared community space is a person's decision.
