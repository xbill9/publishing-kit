# Advocu, measured

**Optional, and GDE only.** [app.advocu.com](https://app.advocu.com/activities) is
where a Google Developer Expert records activities. It is not part of publishing —
the article is already out by the time it matters — so nothing in this kit calls
`make-advocu.py` automatically and nothing depends on it.

Everything below was established in the Google Developer Experts workspace on
2026-09-01.

## The AI route takes a link, not your post

`Add new activity` → `New activity` → `Content creation` offers two paths:

| Route | What it wants |
| --- | --- |
| **Generate your activity with AI** | *"Just paste the link to the activity you want to add"* — a **URL field** |
| **Regular form** | the seven fields below, filled by hand |

The AI route does **not** take the text of your LinkedIn post. It takes a link and
reads the page itself. So an unpublished article cannot use it, and neither can a
LinkedIn post that has not been posted.

### What it produces, driven for real on 2026-09-01

Pasting the dev.to URL is the whole interaction — **there is no submit button to
press.** The field accepts the URL and the modal moves to a skeleton "Content
details" on its own.

What came back, against the sheet `make-advocu.py` had already written:

| Field | The AI's answer |
| --- | --- |
| Title | **identical** to the article's own |
| Date published | **2026-09-01, matching dev.to's `published_at` exactly** |
| Link to Content | the URL as submitted |
| Tags | AI, Build with AI, Open Source — its own choice, from Advocu's picker |
| What was it about? | its own third-person prose |

The description is the part to read before keeping. It opened *"This article
introduces `publishing-kit`, an open-source Claude Code skill designed to
automate and streamline…"* and went on to *"Authored by [name], a Google
Developer Expert, the piece details how the tool handles various aspects of…"* —
third person, about the author, and it left a markdown backtick pair sitting
literally in the text. Replacing it with the article's own `description:` is one
range-select and an `insertText`.

**The fields do not all arrive at once.** Reading the form nine seconds in showed
reach and date still empty; they were populated later. A read that early makes
you conclude the AI left them blank, which is a conclusion about your timing.

**Whether the AI fills the reach field is NOT established.** A value appeared
there that the author had not typed as far as the log shows — but the author was
editing the same form in the same seconds, and there is no way after the fact to
tell an AI-populated field from a hand-typed one. Two candidate sources and no
control, so it is written down as unresolved rather than as an Advocu behaviour.
Check the number yourself before submitting either way; that is the one field
where being wrong is reported to a program.

## The form

Step 1, "Content details":

| Field | Required | Notes |
| --- | --- | --- |
| Content type | yes | Articles, Books, Code contribution, Demos, Newsletters, Podcasts, Videos |
| What was the title? | yes | |
| What was it about? | yes | rich text: bold, italic, underline, strike, link, ordered and unordered lists |
| Tags | no | picker |
| How many people read your content? | yes | a number |
| Date published | yes | |
| Link to Content | **yes** | `https://` |

Step 2 is "Additional information". There is a **Save as draft**, so an activity
parks exactly like a draft on every other destination here — and the workspace
keeps a `Drafts` tab beside `Activities`.

## Publication is a precondition, not a final step

`Link to Content` is required and the AI route is a URL field, so **an activity
cannot be filed before the article is public.** That inverts the usual order: for
every other destination the kit builds first and publishes last; here publishing
comes first and Advocu is the tail.

`make-advocu.py` fails rather than emitting a sheet with a placeholder link, and
it rejects a dev.to draft URL outright, because a `-temp-slug-` link changes the
moment the article is published.

## Reach is a measurement

"How many people read your content?" goes into someone's program statistics.
`make-advocu.py` will read it from dev.to's own `page_views_count` when the link
is a dev.to article, and otherwise leaves it blank with a warning. It will not
guess. It reads **Date published** from the same response's `published_at`, for
the same reason: the API knows it exactly, so remembering it is a made-up figure
waiting to happen.

A counter reading **0** gets its own warning rather than being passed along
quietly. Zero is what the counter says an hour after publishing, and it means
"too early to tell", not "nobody read it" — park the draft and put a real number
in before submitting. A number invented here is worse than an untraced figure in an article,
because an article's readers can check it and a program's statistics cannot.

## Driving the form: Ant Design, and focus does not follow a click

The form is Ant Design. Two things cost time:

- **Associate a label with its control through `.ant-form-item`, not by walking
  up parents.** Walking up from the label's parent until an `<input>` turned up
  returned a *different, wider* field — focusing that and typing would have
  written the reach figure into another box.
- **A click on the reach input did not move focus out of the rich-text
  description above it.** The typed character landed mid-word in the description
  (`versi0ons`) — the same race as clicking into Medium's editor and landing in
  the Title. Focus the element in JS, assert `document.activeElement` is it, and
  only then type.

Setting the value with the native setter plus an `input` event did **not** stick:
the field cleared. Ant's controlled inputs want real keystrokes.

Step 2 holds an optional rich-text "Additional information", an image upload
(JPG/PNG/GIF/WEBP), and a *"Do you want to make this activity private?"* toggle,
with **Submit** and **Save as draft**. Note that Submit sits at almost exactly
the coordinates Next occupied on step 1 — do not click that position twice
without re-reading the page.

## Two other activity types exist

`Add GitHub activity` and `Add YouTube activity` sit beside `Add new activity` and
take a repository or a video rather than a link to an article. Out of scope here,
but worth knowing they are separate paths rather than content types inside the
same form.
