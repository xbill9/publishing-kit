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
guess. A number invented here is worse than an untraced figure in an article,
because an article's readers can check it and a program's statistics cannot.

## Two other activity types exist

`Add GitHub activity` and `Add YouTube activity` sit beside `Add new activity` and
take a repository or a video rather than a link to an article. Out of scope here,
but worth knowing they are separate paths rather than content types inside the
same form.
