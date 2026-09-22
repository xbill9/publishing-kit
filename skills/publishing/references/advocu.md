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
introduces `publishing-kit`, an open-source Codex and Claude Code skill designed to
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

## The activity carries the article's cover, as WebP

Advocu accepts WebP for an activity's image (author's report, 2026-09-15), so
`make-advocu.py` now writes `advocu-<stem>-cover.webp` beside the sheet and names
it under `## Cover image`. The source is `--cover FILE`, else a `builder-cover*`
beside the article — the 16:9 Builder Center cover, the shape a card shows best —
else the local file named by `cover_image:`. **No cover found is a FAIL**;
`--no-cover` opts out.

The image is converted, never cropped, and scaled down only past 1600px wide. On
the Kiro CLI 3 article: `builder-cover.d558caf2.jpg` 1200x675 became a 57 KB WebP.
Advocu's own size and dimension limits are **not measured** here; read the
upload widget's hint when attaching, and record what it says in this file.

## Filing the activity in a browser, measured

MEASURED 2026-09-15, filing the Kiro CLI 3 article through the regular form with
its WebP cover.

- **The image is on step 2, "Additional information"**, not step 1: "Please
  provide an image for your activity — Drop image here or click to select — You
  can upload JPG, PNG, GIF or WEBP file". That hint is the first-party
  confirmation of WebP. Its `<input type=file accept="image/jpeg,image/png,image/gif,image/webp">`
  is in the **light DOM**, so `find` returns a ref and `file_upload` attaches the
  file directly — no proxy input, unlike LinkedIn.
- **Step 2 also holds "Do you want to make this activity private?"**, a switch
  that defaulted **off**. Read it before Submit.
- **The form is Angular with ng-zorro (antd) controls.** Plain text fields
  (title, link, reach) take the native value setter plus `input`/`change`
  events; "What was it about?" is a Quill editor and takes
  `execCommand("insertText")`. Content type opened with a synthetic
  `mousedown` on `.ant-select-selector` and accepted a click on the option.
- **Tags accepted one scripted selection and ignored the second.** "AI" stuck;
  "AI - Gemini" — clicked on the option and on its inner content, with pointer
  events — did not, and the dropdown would not close afterwards. The first
  attempt's script also hung the renderer until `javascript_tool` timed out.
  Tags are optional; do not burn turns on a second one. Advocu's vocabulary has
  `AI - Gemini`, `AI - AI Studio`, `AI - Gemma` and similar, and nothing for
  `mcp` or `python`.
- **A typed date looks accepted and is not.** Setting `2026-09-15` in the
  input showed the text, and **Next moved to step 2 without complaint** — but
  Submit failed with *"A problem occurred — Activity did not pass validation."*
  Back on step 1 the field read *"This field is required."*: the form model was
  still empty. Next does not validate step 1, so it proves nothing. Set the date
  by opening the picker and clicking the cell `td[title="YYYY-MM-DD"]`, then read
  the form item's `ant-form-item-has-success` before moving on.
- **Previous drops the uploaded image.** After fixing the date on step 1 and
  pressing Next again, step 2's drop zone no longer listed the WebP. Attach the
  image last, after step 1 is known good, and re-check the filename in the drop
  zone immediately before Submit.
- **Keep Submit and the wait for its result in separate scripts.** One script
  that pressed Submit and then polled for up to 20 s hung the renderer until
  `javascript_tool` timed out at 45 s, leaving it unclear whether anything was
  filed. A short read afterwards showed the validation toast and the form still
  open — nothing filed, no duplicate. Press, return, then poll with short reads.
- **"A problem occurred — Activity did not pass validation." stays on screen.**
  It was still visible after going back and forward between steps without a new
  Submit, so its presence alone does not mean a second attempt failed.
- **What success looks like.** With the date set through the picker and the WebP
  re-attached on step 2, Submit produced *"Success! Your activity has been
  submitted"* — shown **alongside** the stale validation toast, with the form
  still rendered for a few seconds. Judge by the success text, then confirm the
  activity from a fresh load of the Activity Stream rather than from the modal.
- **In a hidden tab the lists did not render, so the toast was the only
  confirmation.** After submitting, a fresh load of the Activity Stream, the
  member profile (which shows only per-type totals, e.g. "272 submitted") and the
  *My activities → Activities (318)* and *Drafts (8)* tabs all showed counts but
  no entries in the DOM or page text — "Total results: 107311" with nothing under
  it. The new activity could not be found there, and neither could any other.
  Whether a new activity also waits on community-manager review before it is
  listed is **not established**. Check the list in a visible browser window.
- **The tab was hidden**, as with every other editor this session: all presses
  went through JS.

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

## The date picker, measured again on 2026-09-16

Two things made the date field look broken when the cause was elsewhere. The
existing note above — that a *typed* date passes Next and then fails Submit — still
holds; these are about driving the picker itself.

**A coordinate from `getBoundingClientRect()` is not a click coordinate.** The
click frame here was 1568x714 while `window.innerWidth/innerHeight` was 1701x775,
a factor of **0.92**. Clicking a cell's CSS centre directly landed roughly 70px
right and 30px down — one row and two columns away — and quietly selected
**2026-09-25** instead of 2026-09-16, with the form item still reporting
`ant-form-item-has-success`. Scale every JS-derived point before clicking:

```js
const sx = 1568 / window.innerWidth, sy = 714 / window.innerHeight;  // read the frame from the screenshot result
const r = cell.getBoundingClientRect();
const clickAt = [(r.left + r.width / 2) * sx, (r.top + r.height / 2) * sy];
```

This is the same gap `browser-publishing.md` records under "The screenshot is not
in CSS pixels, and the gap is silent". It bites hardest on a calendar, because
every wrong answer is still a valid date.

**The picker closes between tool calls.** Measuring the cell in one
`javascript_tool` call and clicking in the next read a panel that no longer
existed: `.ant-picker-dropdown` count went from 3 to 0, `td[title="2026-09-16"]`
from present to absent, and the clicks appeared to be ignored. Two coordinate
clicks and one JS press were all spent on a dead panel.

**Do the whole interaction in one script** — open, wait for the panel, find the
cell, press it, read the input back:

```js
press(dateInput);                                   // opens the picker
let panel = null;
for (let i = 0; i < 20 && !panel; i++) {
  await sleep(250);
  panel = [...document.querySelectorAll('.ant-picker-dropdown')]
    .find(d => visible(d) && !d.className.includes('hidden') && d.querySelector('td[title]'));
}
press(panel.querySelector('td[title="2026-09-16"] .ant-picker-cell-inner'));
await sleep(1000);
dateInput.value === '2026-09-16';                   // the only check that counts
```

Scope the cell lookup **to the open panel**, not to `document`: a bare
`document.querySelector('td[title=…]')` can return a cell in a stale panel, the
same first-match trap as Medium's hidden editor.

## Step 2's image input, and what success looks like

Confirms and extends the note above. The input is in the light DOM with
`accept="image/jpeg,image/png,image/gif,image/webp"` and carries **no accessible
name**, so `find` cannot see it until one is added:

```js
document.querySelector('input[type=file]').setAttribute('aria-label', 'Advocu activity image input');
// then: find "Advocu activity image input" -> ref, file_upload(cover.webp, ref)
```

**After a successful upload `input.files` reads 0** — the app consumes the file
into its own state, exactly as Slack does. Judge by the filename appearing in the
drop zone and a preview thumbnail rendering (200x200 here), never by the input.

"Do you want to make this activity private?" read `false` on arrival, matching the
earlier run.

**Save as draft is confirmed by the Drafts count, not only the toast.** The toast
read *"Success! Activity has been saved as draft"* and the **Drafts tab went 7 to
8** in the same view — a 1200x675 WebP of 13 KB attached, in a visible browser
window where the lists render.

## Tags are Google's product taxonomy, not the article's tags

MEASURED 2026-09-22. `make-advocu.py` writes the dev.to front matter's tags into
the sheet's **Tags** field -- `googlecloud, python, devops, opensource` for one
article. **Advocu's Tags field takes none of them.** It is a fixed vocabulary of
Google product areas: `AI - Gemini`, `AI - TPU`, `Cloud - Compute, Networking,
Storage`, `Cloud - Operations & Management`, `Cloud - Security`, `Google Cloud`,
`Open Source`, and so on. A free-text tag is simply not selectable.

So treat the sheet's Tags line as a prompt to go and choose, not as a value to
copy across. What that article took in the end:

    Google Cloud
    Cloud - Compute, Networking, Storage
    Cloud - Operations & Management
    Open Source

**The picker is virtualised**, exactly as Builder Center's is. With nothing typed
the DOM holds only the first alphabetical page -- every option read back was
`AI - *`, and a search for anything containing "cloud" over that DOM returned
nothing, which reads as "there is no Cloud tag". Type the term first, then read
the options.

## Driving the Regular form

MEASURED 2026-09-22. The form is Ant Design and it is two steps: **1 Content
details**, **2 Additional information**, with `Save as draft` available on both.

- **Text fields need the native value setter**, not `el.value = x`: React does
  not see a plain assignment. `Object.getOwnPropertyDescriptor(HTMLInputElement
  .prototype, "value").set.call(el, v)` then `input` and `change` events.
- **"What was it about?" is a rich-text `contenteditable`**, not an input.
  `execCommand("insertText")` fills it.
- **Content type and Tags render their selection outside the input** -- the
  input's own `value` stays empty after a pick, so read the ancestor's text or
  the chips instead of concluding nothing happened.
- **Date published is an `ant-picker`.** The cell to click carries
  `ant-picker-cell-in-view`; the same day number also appears as a greyed
  adjacent-month cell, so match on that class rather than on the number alone.
  Click `.ant-picker-cell-inner`.
- **The image is an `ant-upload` dragger and its input is hidden.** `file_upload`
  to a light-DOM proxy input, then copy `files` across with a `DataTransfer` and
  dispatch `change`. **The dragger keeps its "Drop image here or click to select"
  prompt visible after a successful attach**, so that text is not evidence the
  upload failed -- look for an `.ant-upload-list-item` carrying the filename, and
  check it has no `error` class.

A saved draft moves the sidebar count: `Drafts (0)` became `Drafts (1)` and the
toast read `Activity has been saved as draft`. Submitting is the author's call.

## Two readings that lie on the Regular form

MEASURED 2026-09-22, filing a draft with every field and the WebP cover.

- **`ant-form-item-has-success` is on every field before anything is typed.**
  All seven step-1 items carried it with Content type still empty, so it says
  nothing about whether a field took. Read each value back instead: the input's
  `value`, the Quill editor's `innerText`, and for the two selects the
  `.ant-select-selector` text and the `.ant-select-selection-item` chips.
- **A select's dropdown outlives the pick, and a document-wide option search
  reads the wrong list.** The Content type panel stayed open after `Articles`
  was chosen, so typing `Gemma` into Tags and then searching every
  `.ant-select-dropdown` returned the seven content types and no tag. Scope the
  search to the dropdown that is not the content-type list (it opens with
  `AI`, `AI - Agent Development Kit (ADK)`, ...), then press the option; that
  committed `AI - Gemma` first time. Content type still read `Articles`
  afterwards -- check it anyway, since both selects share the overlay.

The save itself matched the note above: the toast rendered twice, the Drafts
count went 0 to 1 once, and a fresh load of the Activity Stream still read
`Drafts (1)` with the Activities count unchanged.
