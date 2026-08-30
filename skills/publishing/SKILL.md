---
name: publishing
description: Trigger when writing up or publishing a technical article to AWS Builder Center, dev.to, or Medium — including "write this up", "make an article", "builder center", "dev.to post", "medium version", "cover image", or turning a benchmark or deployment into a paper. Covers the three destination formats and their incompatibilities, the table/code-to-image generator, mandatory cover images, and a pre-flight check that fails the build.
---

# Publishing a technical article

Three destinations, **three different artifacts, not three copies of one.** They
disagree about tables, about code blocks, and about cover images, and every
disagreement fails silently — you get a plausible-looking file that the
destination quietly mangles.

Run `scripts/check-article.py` before publishing anything. It exits non-zero.

## Pre-flight

```
python3 scripts/check-article.py <article>.md --repo-root <repo>
```

It enforces, in order of how silently each fails:

1. **A cover image exists.** See below — this is not optional.
2. It is referenced by `cover_image:` and the file is actually there.
3. It is **committed**, because the URL is fetched at render time.
4. Geometry matches the destination.
5. `published: false`.
6. `title` / `description` / `tags` present.
7. Medium artifacts point at *this* article's directory and their PNGs exist.
8. No empty link targets.

## Proof-reading: no unverified facts

An article is a set of assertions, and the ones that embarrass you are numbers
carried in from memory. **Never restate a figure from prose** — not from another
article, not from a code comment, not from a chat log. Prose is not evidence.
Figures that live only in prose have repeatedly turned out to have no artifact
behind them at all.

```
python3 scripts/check-facts.py article.md --evidence run.json results.csv logs/
```

It extracts every checkable claim — prices, measurements, quantities, versions,
cloud identifiers, arch strings — and reports which appear in **no** evidence file.
It cannot tell you a number is true; it tells you which numbers you are asserting
without an artifact, which is where wrong numbers come from. Fenced code blocks
are skipped, because pasted tool output is itself evidence.

Every untraced claim is exactly one of three things:

1. **Measured, but you did not archive the artifact.** Fix by archiving it. If the
   machine is gone, save the captured output verbatim with a header saying where
   and when it came from — that file is now the citation.
2. **Arithmetic.** Legitimate, but *label it as arithmetic in the text* and record
   the derivation. A theoretical peak is not a measurement and must never be
   quoted as one.
3. **Asserted from memory.** This is the one to fix. Go and measure it, or cut it.

Standing exemptions go in a `.factsignore` beside the article, **one per line with
the reason written above it**. If you cannot write the reason, the claim needs an
artifact instead, not an exemption.

Two other things a script cannot do, so do them by hand:

- **Check vendor and identity claims**, not just numbers. Archiving the EC2
  instance-type data for one article surfaced that two instance families had been
  described with the wrong host CPU vendor throughout.
- **Re-read every comparison for what varied.** If two measurements differ in
  engine version, harness, or host size, say so in the scope paragraph. State it
  once, plainly, at the end — not as hedging threaded through the body, which
  reads as no confidence and helps nobody.

## Every article needs a cover image

There is no path where skipping it is correct, and **nothing fails locally when
you skip it** — dev.to only fetches the `cover_image:` URL at render time, so a
missing file shows up as a broken image on a published post. The check treats an
absent or unreferenced cover as a hard failure.

The two destinations disagree:

| | dev.to | AWS Builder Center |
|---|---|---|
| Size | **1376x768** | **1200x675**, max 2 MB |
| Delivery | `cover_image:` URL, fetched at render | uploaded in the editor |
| Text in image | fine | **"Text in images is not recommended"** |

```
python3 scripts/make-cover.py --out devto-cover.jpg --mode devto \
  --eyebrow "..." --headline "line one|line two" --subhead "..." \
  --tile "name|sub|$0.42|per hour|CHEAPEST PER HOUR|orange" \
  --tile "name|sub|$0.60|per M tokens|CHEAPEST PER TOKEN|blue" \
  --footer "..."

python3 scripts/make-cover.py --out builder-cover.jpg --mode builder
```

`--mode builder` defaults to `--no-text` to respect AWS's guidance.

Rules the generator already follows, worth knowing if you edit it: colour rides on
chips and swatches, **never on numerals or labels** — text wears ink tokens. The
two-colour pair is validated with the `dataviz` skill's palette validator rather
than eyeballed. Draw at 2x and downsample or the type looks soft. **Render it and
open it** — a validator checks colour, not layout, and the first pass usually has
a label collision.

## dev.to

Markdown with YAML front matter. Tables, fenced code and emoji all render natively,
so this is the **source** article the other formats are derived from.

```yaml
---
title: "..."
published: false
description: "..."
tags: aws, vllm, cuda, machinelearning
cover_image: https://raw.githubusercontent.com/<user>/<repo>/main/<dir>/devto-cover.jpg
---
```

`published: false` unless told otherwise.

## Medium — use the generator, never hand-write

**Do not write a Medium markdown file by hand.** Medium's importer **strips
markdown tables entirely** and flattens `<pre>` to a single line while stripping
`<br>`, so anything depending on alignment cannot survive as text.

```
python3 scripts/make-medium.py devto-<slug>.md medium
```

It renders every table and box-drawing diagram to PNG at 2x and emits two files:

| File | Use |
|---|---|
| `<slug>-embed.html` | **Prefer this.** Images inlined as base64, self-contained. Open in a browser, Select All, Copy, paste into the Medium editor; Medium re-hosts the images. Pasting also preserves code blocks the importer would flatten. |
| `<slug>-hosted.html` | For `medium.com/p/import`. Requires `medium/img/*.png` committed and pushed first. |

**The image base URL is derived from the article's own directory.** This is the
single most repeated bug in this toolchain: a per-project copy of the script used
to hardcode its own project path, so a copy taken elsewhere pointed every `<img>`
at the original project's URLs — all 404 — while the embed variant hid it
completely because its images are inlined. Override with `--img-base=<url>` when
the images will not be served from `<repo>/<article-dir>/medium/img/`.

More importer quirks — the silent killers around figure captions, the URL-keyed
cache, canonical-link resolution, heading sizes — are in `references/medium.md`.

## AWS Builder Center

`builder.aws.com`. **This is AWS, not Google.** Searching for "Builder Center" as
a Google property finds nothing.

- Drafts: `builder.aws.com/profile/content?tab=draft`
- New article: **"+" in the top bar → Article.** Do not open an existing draft's
  preview and edit it — that overwrites the existing piece.
- Fields: **Title** (255), **Description** (512), **Body**, plus a cover upload.
- **Tables and multi-line code blocks both render correctly**, unlike Medium. No
  image conversion needed; code shows with line numbers.
- The editor **autosaves** — a "Saving…" indicator, no save button.
- **No emoji** in the house style there.
- **Required closing line:** *"Any opinions in this article are those of the
  individual author and may not reflect the opinions of AWS."*

### Getting the body in

Title and Description are ordinary inputs — click and type.

The body is a `contenteditable` div with no exposed editor handle. **A synthetic
paste event carrying `text/plain` markdown works** and converts properly —
headings, real tables, line-numbered code:

```js
const ed = document.querySelector('[contenteditable="true"]');
ed.focus();
const dt = new DataTransfer();
dt.setData('text/plain', md);
ed.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
```

`dispatchEvent` returns **`false`** — that is `preventDefault`, not refusal. Verify
by screenshot, never by return value.

The real obstacle is getting ~15 KB of markdown into the page. Two routes are
closed: cross-origin `fetch` of the raw markdown is **blocked by CSP**, and the
system clipboard (`wl-copy` / `xclip`) hangs the shell holding the selection. So
either inline the markdown in chunks, or let a human paste it. Strip the `# `
title and any subtitle line first — those are separate fields.

**Never click Publish.** Leave it as a draft and hand back the link.

## House style

Voice, section order, opener and closing formulas live in
`references/house-style.md`. Swap that one file to retarget this skill to a
different author or publication; nothing else here depends on it.
