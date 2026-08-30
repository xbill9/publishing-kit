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
caption. **The first image in the body becomes the story's cover.** Alt text is
worth writing — it is the accessible equivalent and it survives.

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
