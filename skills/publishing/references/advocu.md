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

## Reach is an estimate, and it says so

"How many people read your content?" cannot be measured for an article that ran
in five places. Only dev.to exposes a count over an API, it reads 0 for hours
after publishing, and the copies cannot be summed — the GDE and aws-builders
copies are different URLs with different counters, and Medium and Builder Center
have no API at all.

So `make-advocu.py` writes the author's standing estimate, **3000**, and labels
it in the sheet: `3000 (standing estimate, not a counter reading)`. It reports
dev.to's `page_views_count` alongside it and never substitutes it.

The labelling is what keeps this consistent with the kit's rule against invented
figures. That rule exists because a number *presented as a measurement* invites
a reader to trust it as one. An estimate the author owns, marked as an estimate,
is not that — and a `page_views_count` copied silently into the field would be
the worse of the two, because it looks sourced while understating the activity
by four destinations.

`--reach N` overrides it when a real number exists. **Date published** is still
read from the same response's `published_at`, because that one genuinely is a
measurement and the API knows it exactly.

## Two other activity types exist

`Add GitHub activity` and `Add YouTube activity` sit beside `Add new activity` and
take a repository or a video rather than a link to an article. Out of scope here,
but worth knowing they are separate paths rather than content types inside the
same form.
