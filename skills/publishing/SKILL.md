---
name: publishing
description: Trigger when writing up or publishing a technical article to AWS Builder Center, dev.to, Medium, or LinkedIn — including "write this up", "make an article", "builder center", "dev.to post", "medium version", "linkedin post", "announce the article", "cover image", or turning a benchmark or deployment into a paper. Covers the four destination formats and their incompatibilities, the table/code-to-image generator, mandatory cover images, the LinkedIn draft whose links must resolve, and a pre-flight check that fails the build.
---

# Publishing a technical article

Four destinations, **four different artifacts, not four copies of one.** They
disagree about tables, about code blocks and about cover images. LinkedIn renders
no markup at all. Every disagreement fails silently: you get a plausible-looking
file that the destination quietly mangles.

Run `scripts/preflight.py <article>.md --live` before publishing anything. It runs
every check and exits non-zero. Without `--live` nothing fetches a published URL,
and local state has been wrong before.

## Three ways this kit has been wrong, repeatedly

Every check here exists because something shipped broken. These three are the
*shapes* those failures keep taking, and each one was hit more than once. Check
for them before adding a fourth check.

**1. One observation generalised into a rule.** Builder Center preserves newlines
inside a paragraph — measured, true, and written up as a Builder Center quirk. The
unstated half was that dev.to therefore folds them, which nobody measured, and 47
of 62 paragraphs in a published article had been rendering ragged for months. The
cover was "1376x768, the house size" without anyone asking what dev.to displays;
it displays a 2.381:1 crop and had been cutting the eyebrow and footer off every
article. **A property of one destination is evidence about that destination only.**

**2. Identity mistaken for freshness.** Three times, in three places. A cover was
*tracked by git*, so the check passed, while the published URL served an older
image because it had been regenerated after its commit. `claude plugin update`
compares *version strings*, so it answered "already at the latest version" for
content six commits newer. `skill-footprint.py` shipped that same bug on its first
day. **"Is it the right thing" and "is it the current thing" are different
questions, and the second one is the one that breaks silently.**

**3. A measurement with no control.** A first read of a published article counted
23 "bare" fences and looked like proof that dev.to does not relabel them — they
were closing fences, and parsed as pairs the article proved the opposite. The
checksum recommended below cried corruption on a payload that had transferred
perfectly, because one side counted UTF-16 units and the other counted code
points. **Before believing a negative result, prove the test can produce a
positive one.** The Medium wrap test pasted a control paragraph with real `<br>`
in it for exactly this reason, and that control is why its zero means something.

A corollary that follows from all three: **simulate the destination, do not assert
about it.** `check-article.py` no longer compares the cover against a remembered
geometry, it computes the band dev.to would crop and looks for ink in it.
`check-links.py` does not reason about whether a file was pushed, it fetches the
URL and compares the bytes.

## How each destination is pushed

**This is the split that decides the whole workflow.** One destination has a real
API. Two have none and need a browser driven for them. One has an API that cannot
draft.

| Destination | How the article gets there | Draft state |
| --- | --- | --- |
| **dev.to** | **REST API, and it is complete** — create, update in place, list, and set `organization_id`. No browser, ever. | `published: false` |
| **Medium** | **Claude Code driving Chrome.** Paste `-hosted.html` into the editor. No publishing API exists. | editor draft |
| **AWS Builder Center** | **Claude Code driving Chrome.** Chunked injection into the `contenteditable`. No publishing API exists. | autosaved draft |
| **LinkedIn** | API exists, but `PUBLISHED` is the only state accepted on creation, so posting through it *is* publishing. | composer only |

So the browser work is not laziness about reading API docs — for Medium and
Builder Center **there is no API to read.** Everything in
`references/browser-publishing.md` exists because those two destinations can only
be reached by driving their editors, and driving an editor is where the clipboard
races, the duplicate pastes and the silent `data:` stripping all live.

The corollary is the rule worth remembering: **before reaching for the browser on
any destination, check whether that destination has an API.** dev.to's was sitting
unused in eight directories while a browser flow was built around it.

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

**Scope `--evidence` to text artifacts, or the check lies to you.** It compares on
digits alone, so pointing it at a run directory containing compressed traces and
protobufs (`*.trace.json.gz`, `*.xplane.pb`, read with `errors="ignore"`) produces
**coincidental matches against binary noise**. A first pass reported `15 traced, 0
untraced`; re-run against only the `.md` / `.json` / `.txt` artifacts it became `14
traced, 1 untraced`, and that one was a real drifted figure that had no artifact
anywhere. Two other "traced" claims were also false: `4.35 s` matched `4.355` (a
kernel duration in ms) and an `SM 8.9` claim matched `8.976` inside a file for the
*other* GPU.

So: a green result from a directory full of binaries is not evidence of anything.
Feed it text, and sanity-check *which file* each claim traced to — the tool reports
the first match, not the best one.

**And a green result from a path that does not exist is worse.** `preflight.py`
defaulted `--evidence evidence/` and `--repo-root ..` *relative to the current
directory*, so they were right only when run from the scripts directory. Run from
the repo root, check-facts read an evidence directory that was not there and
printed `0 claim(s) against 0 evidence file(s)` / `0 untraced` — a clean pass over
nothing — while check-article called a committed cover uncommitted. Both defaults
now anchor to the article (`git rev-parse --show-toplevel` from its directory, and
`<article dir>/evidence`), preflight prints all three resolved paths before it
runs anything, and **check-facts now exits 1 if an evidence path is missing or
holds no readable file** rather than reporting success for having read nothing.

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

**Author at the ratio that is displayed.** MEASURED 2026-08-31: dev.to does not
show the cover you upload. Its proxy renders `width=1000,height=420,fit=cover` — a
**2.381:1 centre crop**. A 1376x768 cover loses **95px off the top and 95px off the
bottom**, which sliced the eyebrow through its letterforms and cut the footer
entirely, in every article shipped at that size. `--mode devto` now emits
**1376x578**, which is 2.381:1, so nothing is cropped.

The pre-flight simulates the crop: it fails when ink falls in the bands dev.to
would discard, and warns when the ratio is wrong but nothing is drawn there.

The two destinations disagree:

| | dev.to | AWS Builder Center |
|---|---|---|
| Size | **1376x578** | **1200x675**, max 2 MB |
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

### Name the cover by its bytes

**A cover URL is a mutable name, and dev.to treats it as permanent.** MEASURED
2026-08-31: dev.to does not re-host a cover, it **proxies** it, with your URL
embedded in theirs —
`media2.dev.to/dynamic/image/.../https%3A%2F%2Fraw.githubusercontent.com%2F...`.
So the URL you hand it is load-bearing for the life of the post, and a proxy keyed
on that URL decides for itself when to look again.

Two failures follow, both silent. Regenerate a cover in place and the published
article may keep serving the old image. Reuse a filename across articles and the
older one silently repaints.

```
python3 scripts/make-cover.py --out devto-cover.jpg --mode devto \
  --content-address --url-base "https://raw.githubusercontent.com/<u>/<repo>/main/<dir>"
```

```
wrote devto-cover.6d805f0f.jpg  1376x578   84 KB
cover_image: https://.../devto-cover.0d021e90.jpg
```

A hashed name is a URL nothing has cached, and the old file stays put so published
articles keep rendering. Same reasoning as Medium's importer cache in
`references/medium.md`, where `?v=2` does not bust it either. Regenerating
identical bytes yields the identical name, so the flag is idempotent.

The pre-flight checks that a hashed name still matches its bytes, and **warns on a
cover without one.** Do not edit a content-addressed file in place.

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

**Unwrap paragraphs before posting.** dev.to renders with hard breaks on, so a
hard-wrapped source publishes with a line break at every wrap. `publish-devto.py`
unwraps on the way out and leaves the repo copy readable; `--no-unwrap` opts out.

### Post it with the API, never the browser

**This repo ships the wrapper: `scripts/publish-devto.py`.**

```
python3 scripts/publish-devto.py --list
python3 scripts/publish-devto.py --create <article>.md --org-slug gde
python3 scripts/publish-devto.py --update <id> <article>.md
python3 scripts/publish-devto.py --org <id> aws-builders
```

**The pre-flight gates the publish.** `--create` and `--update` run
`check-article.py` first and refuse on any FAIL, because every check in it
describes something invisible locally and permanent once published. `--force` is
deliberate and should be rare.

The key is read from `$DEV_TO_API_KEY` or `~/.devto.key`, never from the command
line, where it would land in shell history and process listings. `--org-slug` on
create routes the article in the same run.

**dev.to has a REST API and this repo already wraps it.** `publish-devto.sh` takes
any article path — but **the copies are not all the same script.** MEASURED
2026-08-30 in `gemma4-dev`: of seven copies, only `gpu-vllm-g5g-2b/publish-devto.sh`
implements the flags; the other six take one positional argument and always POST a
new draft, so `--update` is read as a filename and dies with `missing --update`.
Check before reaching for a flag:

```
grep -l -- --update */publish-devto.sh          # which copies can update

bash <any-rig>/publish-devto.sh <article>.md          # create a NEW draft (all copies)
bash <flagged-rig>/publish-devto.sh --list            # ids + published state
bash <flagged-rig>/publish-devto.sh --update <id> <file>  # overwrite in place
```

**`published` is not a settable field.** MEASURED 2026-09-01:
`PUT {"article": {"published": true}}` returns **200 and changes nothing** — the
article stays in `/articles/me/unpublished`. dev.to reads the flag from the front
matter inside `body_markdown`, so publishing means resending the body with
`published:` flipped. The 200 is the trap: it reports success for a request that
did nothing, and only the listing shows the truth.

`publish-devto.py --publish <id>` does it properly — fetches the current body,
flips the front matter in the payload only, and then **verifies from the listing**
rather than trusting the response. The source file stays `published: false` so the
pre-flight keeps meaning something. `--unpublish` goes back, and is the only way
back, since there is no delete.

**A slug is fixed at creation and a rename does not move it.** A draft made under
a working title keeps that title's URL after you retitle it, so create it with the
title you mean to publish under. Replacing the draft is the only fix, and the two
creates need five minutes between them: the same title twice inside that window is
refused with 422 `Title has already been used in the last five minutes`.

**A draft will never be byte-identical to its source file.** dev.to labels bare
` ``` ` fences with a detected language (` ```shell `, ` ```plaintext `) on the way
in, so diff the two below that substitution rather than concluding the upload
drifted.

It reads the key from `$DEV_TO_API_KEY` or `~/.devto.key` and never takes it on the
command line. Front matter is part of `body_markdown`, so title, tags and
`cover_image` all transfer — no field-filling, no cover upload, no title retyping.
`--update` rewrites those too, and does not change the slug of an already-published
article, so existing links survive.

### The org versions are the SAME article, not a rewrite

MEASURED 2026-08-31 against this account's own back catalogue: the same piece
posted to two communities is **byte-identical**. "Build an MCP server in Rust
with rmcp" is 18,234 characters under `gde` and 18,234 characters under
`aws-builders`, same title, and `diff` on the bodies returns nothing.

So one source file goes to both, and `organization_id` is the only difference.
Writing a second, differently-angled version for the other community doubles the
maintenance and guarantees drift — which is exactly what it did here before
anyone checked the back catalogue. Rotate the angle only when the *subject*
differs, the way an ADK piece and a Bedrock piece genuinely do.

### Publishing under an organization is an API field, not an editor dropdown

An article's community channel (`dev.to/<org>/<slug>` rather than `dev.to/<user>/<slug>`)
is set with `organization_id`, so it needs no browser either:

```
curl -s https://dev.to/api/organizations/<slug>            # the org's numeric id
curl -s -X PUT https://dev.to/api/articles/<id> -H "api-key: $KEY" \
  -H "Content-Type: application/json" -d '{"article":{"organization_id":<n>}}'
```

There is no "list my organizations" endpoint. Recover the ones the account belongs
to by scanning its own back catalogue — `/api/articles/me` carries an `organization`
object on every article that has one:

```
curl -s -H "api-key: $KEY" "https://dev.to/api/articles/me?per_page=40" \
  | python3 -c "import json,sys;print({(x.get('organization') or {}).get('username') for x in json.load(sys.stdin)})"
```

MEASURED 2026-08-30: `gde` (11939) and `aws-builders` (2794) for this account, and the
back catalogue also shows the routing convention — Gemma/JAX pieces to `gde`, EC2/AWS
pieces to `aws-builders`. Front matter cannot express this, so it is a separate call
after the article exists. A later `--update` from source does **not** clear it (tested),
and the old `/<user>/<slug>` URL keeps resolving after the move, so links already handed
out survive.

**Two odd things about published articles' ids.** `GET /api/articles/<id>` returns
`{"error":"not found","status":404}` for some published articles even with a valid key,
while the same article appears normally in `/api/articles/me` — so read state from the
listing, not the by-id endpoint, before concluding an article is gone. And dev.to
allows at most **four tags**; adding a fifth silently keeps the first four.

**Do not drive dev.to's editor in a browser.** It is slower, it needs the clipboard
or a JS bridge, it silently splits front matter across separate title/tag/cover
widgets depending on which editor version the account has, and it is entirely
unnecessary. Before reaching for the browser on *any* destination, check the repo
for an existing publish script — this one was sitting in eight directories while a
whole browser flow was built around it.

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

**The image base URL is derived from git.** This is the
single most repeated bug in this toolchain: a per-project copy of the script used
to hardcode its own project path, so a copy taken elsewhere pointed every `<img>`
at the original project's URLs — all 404 — while the embed variant hid it
completely because its images are inlined. `make-medium.py` asks git for the origin remote, the branch and the article's path
inside the repo, and builds the base from those. Override with `--img-base=<url>`
only when the images will be served from somewhere other than that repository.

More importer quirks — the silent killers around figure captions, the URL-keyed
cache, canonical-link resolution, heading sizes — are in `references/medium.md`.

**Generate with THIS script, never with a per-article fork of it.** MEASURED
2026-08-30: a `build-gde.py` written beside one article borrowed only the table
rendering from an older copy of this script, so it never inherited the heading
demotion — it emitted 19 `<h2>`, and Medium renders `#`/`##` at title size, so the
story read as 19 titles. A fork does not receive later fixes and nothing warns you;
the defect is visible only in the published rendering. If a wrapper is genuinely
needed, have it *call* this script rather than copy pieces out of it.

**Driving any of these editors in a browser: read `references/browser-publishing.md`
first.** It carries the post-paste verification checklist (images, title, code,
tables, last paragraph — each checked separately, because they fail independently),
why the system clipboard must never be used, the base64 JS-bridge injection, the
`file://` restriction, and the paragraph-unwrapping that Builder Center's editor
needs.

## LinkedIn — the post is a file, because the API cannot draft

**LinkedIn's Posts API cannot create a draft.** `lifecycleState` documents `DRAFT`
as content "accessible only to the author and is not yet published", then states
that `PUBLISHED` **is the only accepted field during creation**. Anything that
posts through the API is publishing. So the artifact is a text file for the
composer, which does have drafts.

```
python3 scripts/make-linkedin.py devto-<slug>.md --api
```

It reads `links.txt` beside the article — `key = url`, one per line — and writes
`linkedin-<slug>.txt`. Five checks, exits non-zero:

1. **Every link resolves.** `PENDING` is written into the file as a visible
   placeholder *and* fails the run, so a post with an unpublished link cannot go
   out by accident.
2. The hook fits the "…see more" fold.
3. The post fits the character limit.
4. **No markdown survives.** LinkedIn renders none of it.
5. **No Unicode pseudo-bold.** Screen readers cannot read U+1D400–U+1D7FF, so the
   headline becomes the least readable part of the post.

**Post text takes no formatting.** The `commentary` field is LinkedIn's `little`
format, whose whole element set is text, mentions and hashtags. No bold, no
italics, no lists, no link markup — `**bold**` and `[label](url)` arrive as their
own punctuation.

**For the API only, every reserved character must be backslash-escaped, whether or
not it is used as markup**: `|  {  }  @  [  ]  (  )  <  >  #  \  *  _  ~`. An
article body is full of them. `--api` writes the escaped variant beside the plain
one. Text pasted into the composer needs no escaping.

**Label the two dev.to links differently.** Two articles routed to two
organizations are two different URLs, and "dev.to" twice reads as a duplicate.

**The shape of the post is `templates/linkedin-post.txt`, not code.** An
announcement is the same few moves every time, and rewriting them per article is
how they drift. Wrap anything that should vanish when empty in `[[key]] …
[[/key]]`, so an article with no `## Summary` drops the lead-in line instead of
stranding it above the links. Swap that one file and every post changes shape —
the same arrangement `references/house-style.md` has with the articles.

Which figures here are first-party and which are third-party consensus, plus the
mention-matching rules, are in `references/linkedin.md`.

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

   **There is a better route when you can navigate the tab:** `window.name`
   survives a cross-origin navigation, so load the payload same-origin from
   localhost, stash it there, then navigate to the editor and read it back. 34,715
   characters carried into Medium intact with no chunk loop at all. See
   `references/browser-publishing.md`.

2. **Verify the whole payload before using it.** Checksum it in the page and
   compare against the same computed locally. Use a NUMERIC checksum: a hex or
   base64 SHA can be redacted in transit and tell you nothing.

   ```js
   let a=0,b=0;
   for(let i=0;i<window.__p.length;i++){a=(a+window.__p.charCodeAt(i))%65521;b=(b+a)%65521;}
   ({chars:window.__p.length, adler_a:a, adler_b:b})
   ```

   **Compute the local side over UTF-16 code units, not code points.**
   `charCodeAt` is UTF-16; Python iterates code points; every emoji counts 2
   against 1. A document with three `🔎` reported 34,715 characters in the browser
   against 34,712 in Python and the checksums disagreed on data that had
   transferred perfectly. `references/browser-publishing.md` has the Python that
   matches.

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

### Hard-wrapped source renders as hard breaks — and NOT only here

Builder Center's paste handler preserves the source's newlines inside a paragraph,
so a file hard-wrapped at ~95 columns renders with a ragged break every ~95
characters. `serve-body.py` unwraps before serving.

**This was written up as a Builder Center quirk and it is not one.** MEASURED
2026-08-31: **dev.to renders with hard breaks ON too.** A published article had
`<br>` in **47 of its 62 paragraphs**, from a source with zero lines ending in the
two spaces that mean an explicit markdown break. The ragged rendering had been
shipping for months, in every article, unnoticed.

Where each destination stands, all measured 2026-08-31:

| Destination | Hard-wrapped source | Unwrap needed |
| --- | --- | --- |
| dev.to | **`<br>` at every wrap** — 47 of 62 paragraphs in a published article | **yes**, `publish-devto.py` does it |
| AWS Builder Center | **preserved on paste** | **yes**, `serve-body.py` does it |
| Medium | **collapsed to spaces**, 0 `<br>` in the editor, positive control passed | no |

Assume every destination preserves your newlines until you have checked that one.
The unwrap logic is in `scripts/bodytext.py` — one implementation, imported by
`serve-body.py`, `publish-devto.py` and `check-article.py`, and the pre-flight
warns when an article still has hard-wrapped paragraphs.

**Keep tables to about five columns.** Seven get squeezed until cells break
mid-token — `g4dn.2x/large`, `g6.xlarg/e`. Move what the prose can carry out of
the table.

### Editing an already-published article

Go to the published URL, open the **"..." menu on the article itself → Edit**.
Do NOT navigate to `/create/content/<id>` — that silently creates a **new empty
draft** instead of editing the existing piece.

**Never click Publish.** Leave it as a draft and hand back the link.

## Optional: announcing in the AWS Community Builders Slack

**Optional, and after the fact.** One message in a community channel with a link
to each destination.

```
python3 scripts/make-slack.py <article>.md --hashtags "#A #B"
```

**The format is the author's own, read out of the channel rather than invented** —
two or three lines of plain context, then `Builder Center Article is here:`,
`Medium is here:`, `Dev.to is here:`, `Linked In is here:`, each with a bare URL
on its own line, then hashtags. That order matters, and so does one detail the
script enforces: **the dev.to link is the `aws-builders` one, never the GDE
copy.** It is an AWS channel.

**Slack renders no markdown.** Its markup is mrkdwn — `*bold*` with single
asterisks, `<url|label>` for links — so the script strips markdown rather than
translating it, matching what the existing posts do.

**It does not post.** It writes a file. The channel had 656 members, and nobody
who has read a message unreads it.

If you do stage it in the browser: the composer is a plain Quill editor at
`[data-qa="texty_input"]` — no shadow root — so `execCommand("insertText")` puts
the whole message in at once. Do that rather than typing, because **Enter sends
in Slack**. Then **press Escape**: the trailing hashtags leave Slack's channel
picker open, and Enter would insert a channel link instead of sending.
`references/slack.md` has the rest.

## Optional: announcing in the GDE Americas space (Google Chat)

**Optional, and after the fact.** The same job as the Slack post, for the other
community.

```
python3 scripts/make-gchat.py <article>.md
```

Same shape — the author's own format, a few lines of context then one labelled
link per destination — because a reader in either room should see something
familiar. **What changes is which copy of the article the room gets:** the AWS
Slack channel gets `dev.to/aws-builders`, the GDE space gets `dev.to/gde`, and
`make-gchat.py` fails on the swap exactly as `make-slack.py` does in the other
direction. The link order flips for the same reason — lead with the copy that
belongs to the room.

The shape is that room's, read out of it: paragraphs separated by blank lines and
links **inline** (`"Dev.to is here: <url>"`) rather than on their own line. **No
lede** — a manufactured "just posting in case this helps anyone else" opening was
the default for exactly one post and got cut before sending, because that opening
belongs to a favour, not to an article announcement. `--lede` is there for the
piece that needs one. The space is threaded, so a post is a new
conversation rather than a line in a stream.

**No hashtags, and that is measured, not taste.** In Google Chat a `#` opens the
same People/Files picker `@` does, with `all / Notify all` first in the list —
Enter with it open inserts a notify-everyone. The control is what makes this
trustworthy: `@` alone and `#` alone both open nothing, so testing only those
would have produced the opposite rule. Both need a following letter.

The composer is a plain `contenteditable` with no shadow root, so
`execCommand("insertText")` puts the message in at once — and it does *not* open
the pickers that real keystrokes do. Assume Enter sends. `references/gchat.md`
has the rest.

## Optional: recording the activity in Advocu (GDE only)

**Optional, and unrelated to getting the article out.** `app.advocu.com` is where
a Google Developer Expert records activities, and it runs *after* publication
rather than as part of it.

```
python3 scripts/make-advocu.py <article>.md --reach <n>
```

MEASURED 2026-09-01. `Add new activity` → `New activity` → `Content creation`
offers **Generate your activity with AI**, which asks you to *"paste the link to
the activity you want to add"* — **a URL field, not your post's text** — or a
**Regular form** with seven fields, of which `Link to Content` is required.

Either way the article has to be **public first**: there is no route that accepts
prose alone. So Advocu inverts this kit's usual order, where publishing is last.
`make-advocu.py` fails rather than emitting a sheet with a placeholder, and
rejects a dev.to `-temp-slug-` URL because that link changes on publish.

**It will not invent the reach figure.** "How many people read your content?" is
read from dev.to's `page_views_count` when it can be, and otherwise left blank
with a warning. That number goes into program statistics, where nobody can check
it against the artifact.

The form has **Save as draft**, so an activity parks like everything else here.
Field list and the two other activity types are in `references/advocu.md`.

## House style

Voice, section order, opener and closing formulas live in
`references/house-style.md`. Swap that one file to retarget this skill to a
different author or publication; nothing else here depends on it.
