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

The embed variant from `make-medium.py` inlines every image as a base64 data URI.
Open it in a browser, Select All, Copy, paste into the Medium editor: images ride
along and Medium re-hosts them, nothing needs to be pushed first, **and code blocks
survive** because the flattening is an importer behaviour.

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
