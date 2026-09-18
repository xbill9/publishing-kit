# Medium's importer, measured

Every item here was established by importing real pages and inspecting the result.
Each cost at least one wasted import, and several fail **silently**, which is what
makes them expensive.

## The three silent killers

Each of these looks like your fix simply did not work.

- **A link inside `<figcaption>` makes Medium drop the whole figure.** No error, no
  placeholder — the image is just not there. Captions must be plain text; put the
  link in a paragraph *after* the figure.
- **The importer caches by URL and ignores the query string.** `?v=2` does not bust
  it. Give the importer a **content-addressed filename** so a changed page is always
  a URL Medium has never seen.
- **`<link rel="canonical">` is resolved by the importer**, so a canonical pointing
  at your stable page serves *that* URL's cached copy no matter which URL you
  submitted. Strip the canonical from the copy you hand the importer.

## What the importer does to your markup

- **`<pre>` is flattened to a single line and `<br>` is stripped**, so multi-line
  code cannot survive as text. Render it as an image; a gist link underneath keeps
  it copyable. Single-line blocks import fine as real code blocks.
- **Markdown tables do not render at all.** Render them as images.
- **No markup produces an embed.** Bare URL, anchor, `<figure>`-wrapped anchor,
  `data-oembed-url` and `<iframe>` were all tested: the first four become plain
  links and the iframe is dropped. Gists cannot be embedded via import — only by
  pasting the URL in the editor afterwards.
- **HTML comments are stripped even when correctly escaped** inside `<pre><code>`.
  A block containing one needs to be an image too.
- **Two heading sizes only.** `#` and `##` both become the big one; `###` and
  smaller become the small one. Use `####` for section headings, or a twelve-section
  article reads as twelve titles.

## What works with no effort

Images. Medium fetches them, rehosts at 800px, and takes `<figcaption>` as the
caption. **The first image in the body becomes the story's cover.**

**Alt text does NOT survive a paste.** MEASURED 2026-09-08, pasting a hosted
HTML file whose ten `<img>` each carried a distinct `alt`: every figure in the
draft came back `alt=""`. The control that makes this mean something is the
author avatar on the same page, which reads `alt="xbill"` — the test can
produce a positive, so the ten empties are real. This file previously said alt
"survives", which holds for **import** and was generalised to paste without
being checked.

**Setting it headlessly works, even in a hidden tab.** MEASURED 2026-09-18:
dispatch `pointerdown/mousedown/pointerup/mouseup/click` on the figure's `img` (the
figure gains `is-mediaFocused`), `.click()` the visible `[data-action="alt"]`
button, select the contents of `.overlay .js-textAreaEditor`, then
`execCommand("insertText", …)` and `.click()` `[data-action="overlay-submit"]`.
All four alts survived to `/p/<id>`. Do one figure per `javascript_tool` call: three
in one script timed out at 45 s in a hidden tab, although two of them had saved.

So on the paste route the alt in your HTML buys nothing, and a table rendered
to PNG reaches Medium with no text at all behind it. Either add the alt in the
editor by hand (click the image, then the alt button), or accept that the
Medium copy is less accessible than the dev.to and Builder Center ones, where
the tables are still real tables.

## Hard-wrapped source is safe here, unlike dev.to

MEASURED 2026-08-31 in Medium's own editor, by dispatching a paste with a
`DataTransfer` carrying two paragraphs and reading the result back out of the DOM:

| Paragraph | Source | In the editor |
| --- | --- | --- |
| hard-wrapped at ~95 columns, plain newlines | 3 source lines | **0 `<br>`, 0 newlines in `innerText`** |
| explicit `<br>` between lines | 3 lines | 2 `<br>`, 2 newlines — **positive control passed** |

The second row is the point: the test could detect breaks, and did, so the first
row's zero is a real result and not a blind spot.

So the ragged-break problem that afflicts dev.to and Builder Center does NOT reach
Medium. `make-medium.py` emits the source newlines raw inside `<p>` — no `<br>`
anywhere in a 66-paragraph document — and both the browser and Medium's paste
handler collapse them to spaces. Confirmed on the generated file too: 35 of 35
long paragraphs have newlines in `textContent` and none in `innerText`, and
`innerText` is what a paste carries.

**Unwrapping before Medium is unnecessary, and unwrapping is not harmful either.**
Do not add a step here.

## Cross-origin fetch into the editor is blocked here too

MEASURED 2026-08-31: `fetch('http://127.0.0.1:...')` from `medium.com/new-story`
fails with a bare `TypeError: Failed to fetch`, identical to AWS Builder Center.
The closed route is a property of both editors, not of one of them. Get content in
through the JS bridge and a synthetic `paste` event with a `DataTransfer`.

`dispatchEvent` returned `false` on the successful paste — `preventDefault`, not
refusal, exactly as on Builder Center. Judge by what landed in the DOM.

## Prefer pasting over importing

Pasting beats importing: **code blocks survive** as real multi-line blocks with
syntax highlighting, because the flattening is an importer behaviour, not an editor
one. Measured 2026-08-30 on a nine-code-block article.

**But paste `-hosted.html`, never `-embed.html`.** This reverses what this file said
before, and getting it wrong costs a full re-do:

> **Medium silently strips `data:` URI images on paste.** The embed variant inlines
> every image as base64, so pasting it drops **every image in the article** — cover
> and all tables — with no error, no placeholder and no broken-image icon. You get
> clean-looking prose with blank gaps where the tables were, and a story with no
> cover. Verified 2026-08-30: 4 of 4 images lost from embed, 4 of 4 survived from
> hosted.

The hosted variant references real `https://` URLs, which Medium fetches and
re-hosts. It needs the images **committed and pushed first**. That is the only cost
and it is worth paying.

**The title never transfers.** Neither variant fills Medium's Title field, even
though `-hosted.html` carries an `<h1 class="title">`. The pasted `<h1>` is dropped
and the Title field stays empty. Type the title in by hand, and check the top of the
document for a stray empty block where the h1 was.

**Always pass `--cover`.** With no `--cover`, `make-medium.py` takes the first
`*cover*.{jpg,png}` **alphabetically** from the article's directory. A directory
holding `builder-cover.jpg`, `devto-cover-aws.jpg` and `devto-cover-gde.jpg` put the
*AWS* cover on the *GDE* article — and since the first body image becomes the
story's cover, the wrong art would have shipped.

Import only when you need a URL-driven flow.

## Driving the importer in a browser

The import form's contenteditable rejects synthetic keystrokes intermittently.
`medium.com/p/import-story?xsrf=<token>&importUrl=<urlencoded>` submits directly
and is far more reliable; lift the token from one manual submit.

When auditing an imported draft, note that Medium's editor lazy-loads and
virtualises, so DOM counts lie until you scroll the whole document — and **imported
content is served from `0*` image URLs while Medium's own editor chrome is `1*`**,
so count only `0*` or you will credit yourself images that are really the
onboarding overlay.

## The publish dialog defaults against you

MEASURED 2026-09-01 on a real publish:

| Setting | Medium's default | |
| --- | --- | --- |
| **Paywall this story** | **checked** | earns under the Partner Program, and locks the story behind Medium membership |
| **Notify your N subscribers** | **checked** | emails every subscriber the moment you click Publish |
| Topics | empty | up to five |

The paywall default is the one to think about hardest when the same article is
free elsewhere. This kit publishes one piece to dev.to and AWS Builder Center as
well, so paywalling the Medium copy asks readers to pay for something linked free
two paragraphs into its own text.

The subscriber notification is not undoable. An email that has gone has gone, so
it is the author's decision and not a default to accept by momentum.

Topics take Enter to commit. Typing a name and clicking the suggestion silently
dropped it twice; typing and pressing Enter worked every time.

## Medium 403s a request with no User-Agent

`curl` with its default header gets **HTTP 403** on a published story URL, while
the same URL returns 200 with any ordinary User-Agent set.

**A User-Agent is no longer enough.** MEASURED 2026-09-15: a published story under
a publication (`medium.com/stackademic/<slug>-<id>`) answered **403 to
`curl -A 'Mozilla/5.0'`** as well, while it opened normally in the browser. Verify a
published Medium story with `get_page_text` in the browser; treat a scripted 403
as unknown, not as dead. The browser also redirected that publication URL to the
author's `xbill999.medium.com` subdomain — expected, and not a different story. Same shape as dev.to
answering `Forbidden Bots`. A link checker that reports a published article as
dead is checking its own headers, not the article.

## `&nbsp;` fixes a dev.to wrap and breaks the Medium table image

MEASURED 2026-09-15. A non-breaking space is the obvious fix for a table cell that
wraps at its space on dev.to, and it works there. `make-medium.py` rasterises
tables through a renderer that does **not** decode HTML entities, so the same cell
reaches Medium as a picture of the literal text `Test&nbsp;1`.

Nothing warns. The markdown is valid, dev.to renders it correctly, the PNG is
generated without error, and the only way to see it is to open the image.

So a fix aimed at one destination gets checked in the other destinations'
artifacts before it ships — the same rule as "a property of one destination is
evidence about that destination only", applied to fixes rather than behaviours.
Prefer a repair that is plain text in every renderer: a label with no space in it
needs no entity anywhere.

## Pasted images can re-host and then revert to a placeholder on save

MEASURED 2026-09-17, three times, across two drafts and two image hosts. This is
the failure mode the "7 of 7 images survived" note above does not cover, and it
is invisible until you reload.

Immediately after dispatching the paste, every figure is correct:

| Checked, right after the paste | Result |
| --- | --- |
| figure slots | 9 of 9 |
| `data-image-id` | 9 distinct, all `0*` — Medium re-hosted all of them |
| placeholders | 0 |

The editor then shows `Saved`. **Reload, and the images are gone**: 5 figures
carrying one shared `1*b31hiO4ynbDLRrXWEFF4aQ.png` id and 0 under `0*`. The rest
of the document is untouched — 138 grafs, 17 `h4` + 1 `h3`, 15 multi-line code
blocks, opening and closing landmarks each exactly once. **Only the images
revert.**

What was ruled out, so the next session does not re-run it:

- **Not the image host.** Reproduced with `raw.githubusercontent.com` and with
  `cdn.jsdelivr.net/gh/...`. All 9 URLs returned 200 with correct content types,
  and all 9 loaded as `new Image()` **from the medium.com page itself** — the
  control that proves the URLs are reachable by that browser.
- **Not a stale or odd URL.** A `main/./medium/img/...` path (what `make-medium.py`
  derives when the article sits at the repo root) and a clean `main/medium/img/...`
  behaved identically.
- **Not re-pasting over a used draft.** Reproduced on a brand-new `/new-story`
  draft pasted exactly once.
- **Not the 5xx.** Medium threw a site-wide gateway timeout during the first run,
  but the failure reproduced twice more after it recovered.

**Counting figures is its own trap here.** `.graf--figure img` and even
`.graf--figure` are *virtualised* — the editor materialises a rolling ~5 of them,
so a full scroll can report 5 figures in a 9-figure document, and repeated scans
return different subsets. The reliable count is FIGURE-tagged entries in
`[...ed.querySelectorAll('.graf')]`, which stays at 9. A first pass at this
concluded "4 images were dropped" off the virtualised count, which was wrong.

**Resolved 2026-09-18: the persisted document does hold the `0*` ids, and the
reloaded editor was the thing lying.** A fresh `/new-story`, title and body each
put in by synthetic paste, 4 figures re-hosted as `0*`. After `Saved` and a reload
the editor showed the same symptom as above: `1*b31hiO4ynbDLRrXWEFF4aQ.png` on two
figures, no id on the other two. The draft's rendered view, `medium.com/p/<id>`
(which redirects to `<handle>.medium.com/<id>`), served all 4 under the exact `0*`
ids the paste produced, cover first. The control is that the same check can
fail: the page's own `1*` chrome image shows up in it, so the absence of the
placeholder there means something.

So **audit images on `/p/<id>`, never in a reloaded editor.** The editor's `1*b31…`
figure is a lazy-load placeholder rather than lost data. The paste route keeps its
images, and there is no reason to fall back to import for them. What the 2026-09-17
runs showed on `/p/<id>` was never recorded; if that view ever shows the
placeholder too, this does not hold.

**Typing into the title fails in a hidden tab; a paste works.** MEASURED
2026-09-18 with `visibilityState === "hidden"`: `computer type` reported success
and the Title stayed empty. Collapsing a `Range` into `.graf--title` and
dispatching a `text/plain` paste filled it, and it survived the reload.
