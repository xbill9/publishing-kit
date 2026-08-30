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
| `<slug>-embed.html` | **Do not paste this into Medium.** Images are inlined as base64, and Medium **silently strips `data:` URIs on paste** — every image in the article disappears, with no error and no placeholder. Useful only where a self-contained single file is wanted for something other than Medium. |
| `<slug>-hosted.html` | **Use this for both paste and import.** Real `https://` image URLs, which Medium fetches and re-hosts. Requires `medium/img/*.png` committed and pushed first. Pasting it (rather than importing) additionally preserves multi-line code blocks, which the importer flattens. |

**Always pass `--cover=<file>`.** With no `--cover` the script takes the first
`*cover*.{jpg,png}` **alphabetically** from the article's directory. A directory
holding covers for several articles will therefore put the wrong art on the story,
and since the first body image becomes Medium's cover, that is what ships.

**Type the title in by hand.** No paste or import route fills Medium's Title field,
even though the hosted variant carries an `<h1 class="title">`.

**The image base URL is derived from the article's own directory.** This is the
single most repeated bug in this toolchain: a per-project copy of the script used
to hardcode its own project path, so a copy taken elsewhere pointed every `<img>`
at the original project's URLs — all 404 — while the embed variant hid it
completely because its images are inlined. Override with `--img-base=<url>` when
the images will not be served from `<repo>/<article-dir>/medium/img/`.

More importer quirks — the silent killers around figure captions, the URL-keyed
cache, canonical-link resolution, heading sizes — are in `references/medium.md`.

**Driving any of these editors in a browser: read `references/browser-publishing.md`
first.** It carries the post-paste verification checklist (images, title, code,
tables, last paragraph — each checked separately, because they fail independently),
why the system clipboard must never be used, the base64 JS-bridge injection, the
`file://` restriction, and the paragraph-unwrapping that Builder Center's editor
needs.

## AWS Builder Center

`builder.aws.com`. **This is AWS, not Google.** Searching for "Builder Center" as
a Google property finds nothing.

- Drafts: `builder.aws.com/profile/content?tab=draft`
- New article: **"+" in the top bar → Article.** Do not open an existing draft's
  preview and edit it — that overwrites the existing piece.
- Fields: **Title** (255), **Description** (512), **Body**, plus a cover upload
  (1200x675 recommended, 2 MB cap) and a **tag picker, 5 maximum**.
- **Tables and multi-line code blocks both render correctly**, unlike Medium. No
  image conversion needed; code shows with line numbers.
- The editor **autosaves** — a "Saving…" indicator, no save button.
- **No emoji** in the house style there.
- **Required closing line:** *"Any opinions in this article are those of the
  individual author and may not reflect the opinions of AWS."*

Tags are a searchable fixed vocabulary, not free text — you pick from their list.
`amazon-ec2`, `generative-ai` and `cost-optimization` exist; **`gpu` does not, and
neither does a usable `inference`** (the matches are `application-inference-profile`
and `aws-elemental-inference`, both unrelated). Search before assuming a tag exists.

The cover uploads through a real `<input type=file>`: locate it with `find`, then
use the upload tool with its ref. **Never click a file input** — that opens a
native picker you cannot see.

### Getting the body in — NEVER use the system clipboard

Title and Description are ordinary inputs — click and type. The body is harder.

**The clipboard is shared with whoever else is at the machine.** A synthetic
Ctrl+C loses the race silently, and Ctrl+V then pastes *their* content into your
editor — while your Ctrl+C clobbers what they had copied, which is the more
expensive half. MEASURED 2026-08-30: someone else's article landed in this draft
twice, and nothing anywhere reported a failed copy.

**And never hand the paste to a human.** Automate it.

**The route that works — fully automated, self-verifying, no clipboard:**

1. **Inject the text in chunks through the JS bridge**, JSON-escaped so you
   control the escaping, appending to one variable and **checking the cumulative
   length after every chunk**:

   ```js
   window.__p = (window.__p || "") + "<json-escaped chunk>";
   window.__p.length            // must equal the expected running total
   ```

   ~1400 characters per chunk. A mismatch means characters were dropped — redo
   that chunk. Never proceed past a mismatch.

2. **Verify the whole payload before using it.** Checksum it in the page and
   compare against the same computed locally. Use a NUMERIC checksum: a hex or
   base64 SHA can be redacted in transit and tell you nothing.

   ```js
   let a=0,b=0;
   for(let i=0;i<window.__p.length;i++){a=(a+window.__p.charCodeAt(i))%65521;b=(b+a)%65521;}
   ({chars:window.__p.length, adler_a:a, adler_b:b})
   ```

3. **Clear the editor with the KEYBOARD, not `execCommand`.**
   `document.execCommand("delete")` over a selected range silently does nothing
   here and the paste then APPENDS — you get the entire article twice, which
   only a landmark count will catch. Click the body, then Ctrl+A, Delete.

4. **Assert the editor is empty, then dispatch the paste.** The assertion is
   what prevents the duplicate:

   ```js
   const ed = document.querySelector('[contenteditable="true"]');
   if (ed.innerText.length > 50) throw new Error("not empty, refusing to paste");
   ed.focus();
   const dt = new DataTransfer();
   dt.setData("text/plain", window.__p);
   ed.dispatchEvent(new ClipboardEvent("paste", {clipboardData: dt, bubbles: true, cancelable: true}));
   ```

5. **Count landmarks afterwards.** The opening sentence, the summary heading and
   the closing line must each appear exactly **once**.

`dispatchEvent` returns `false` — that is `preventDefault`, not refusal. Judge by
the landmark count, never by the return value.

**Closed routes, so you do not spend time on them:** cross-origin `fetch` into
the editor page (CSP `connect-src` — adding a CORS header does NOT help, and the
failure is an identical bare "Failed to fetch" either way); `file://` navigation
(blocked by the extension); `wl-copy`/`xclip` (both hang the shell holding the
selection, even detached with setsid/nohup).

Strip the `# ` title and any `*Subtitle:*` line first — separate fields. Watch the
line numbering: `sed '1,2d'` removes the title and the blank line after it,
leaving the subtitle behind.

### Hard-wrapped source renders as hard breaks

Builder Center's paste handler **preserves the source's newlines inside a
paragraph**. Markdown folds a single newline into a space; this editor does not,
so a file hard-wrapped at ~95 columns renders with a ragged break every ~95
characters — visible only once published. Unwrap paragraphs first;
`serve-body.py` has the logic and leaves code, tables, lists and headings alone.

**Keep tables to about five columns.** Seven get squeezed until cells break
mid-token — `g4dn.2x/large`, `g6.xlarg/e`. Move what the prose can carry out of
the table.

### Editing an already-published article

Go to the published URL, open the **"..." menu on the article itself → Edit**.
Do NOT navigate to `/create/content/<id>` — that silently creates a **new empty
draft** instead of editing the existing piece.

**Never click Publish.** Leave it as a draft and hand back the link.

## House style

Voice, section order, opener and closing formulas live in
`references/house-style.md`. Swap that one file to retarget this skill to a
different author or publication; nothing else here depends on it.
