# Getting 23 KB of Markdown Into AWS Builder Center Without Touching the Clipboard

*Subtitle: A step by step publishing pipeline for AWS Builder Center, dev.to and Medium as a Claude Code skill. Mandatory covers at two geometries, a pre-flight that exits non-zero, and a chunked, checksummed route into the editor that never races the system clipboard.*

This article provides a step by step guide for publishing one technical article to AWS Builder
Center, dev.to and Medium from a single source file. A Claude Code skill and nine Python scripts
are built to simplify the process, and three of them exit non-zero rather than let a broken
artifact ship.

https://github.com/xbill9/publishing-kit

Everything was measured on 2026-08-31, on the run that produced the four versions of this piece.

## What is this project trying to Do?

Publish the same work to three destinations without publishing three broken pages.

The destinations disagree about tables, about code blocks and about cover images. Every
disagreement fails silently. There is no error, no warning and no local symptom. You get a
plausible-looking file, the destination mangles it on the way in, and the published page is the
first evidence.

| Feature | dev.to | AWS Builder Center | Medium |
| --- | --- | --- | --- |
| Tables | native | native | stripped entirely |
| Multi-line code | native | native, line-numbered | flattened to one line |
| Cover | 1376x578 by URL | 1200x675 upload, no text | first body image becomes it |
| Tags | 4 max, free text | 5 max, fixed vocabulary | free |
| Publishing API | **full REST API** | **none** | **none** |
| How you push it | `curl` | Claude Code driving Chrome | Claude Code driving Chrome |

**The bottom two rows decide the workflow.** dev.to has a complete REST API — create, update in
place, list, and set the community channel — so nothing about it needs a browser. Medium and
AWS Builder Center have **no publishing API at all**, so the only way an article reaches either
of them is **Claude Code driving Chrome**: open the editor, get the body in, verify it landed.

That is not a shortcut taken instead of reading the API docs. For those two destinations there
is no API to read. Every browser hazard in this article — the clipboard race, the duplicate
paste, the silently stripped images — is the cost of that one fact.

Builder Center is the sharpest case. It renders tables and code better than Medium does, and it
is the one with no API and the largest body to move.

## Where do I start?

Start with the install. The kit ships as a plugin marketplace, so there is no file copying:

```shell
claude plugin marketplace add /home/xbill/publishing-kit
claude plugin install publishing@publishing-kit
```

```plaintext
Successfully added marketplace: publishing-kit (declared in user settings)
Successfully installed plugin: publishing@publishing-kit (scope: user)
```

The path is a local checkout here. `xbill9/publishing-kit` works the same way — main serves the
marketplace manifest, verified HTTP 200.

Restart the session, then read what the skill costs to carry:

```shell
claude plugin details publishing
```

```plaintext
Component inventory
  Skills (1)  publishing
  Agents (0)
  Hooks (0)
  MCP servers (0)

Projected token cost
  Always-on:   ~190 tok   added to every session

  component   always-on  on-invoke
  publishing       ~190      ~9.5k
```

The 528 character description is what every session pays. The 526 line `SKILL.md` is read only
when what you asked for matches that description. **A skill that puts its knowledge in the
always-on half is one you uninstall.**

## At this point you should have

- Claude Code — 2.1.251 here
- Python 3.13.14 with Pillow 12.3.0, for the cover generator and the table renderer
- A dev.to API key in `~/.devto.key`, mode 600
- A public GitHub repo for the article directory. The dev.to cover and every Medium image is
  fetched by URL at render time
- An AWS Builder Center account at `builder.aws.com`, and a browser you can drive

**This is AWS, not Google.** Searching for Builder Center as a Google property finds nothing.

## Setup the Basic Environment

```shell
git clone https://github.com/xbill9/publishing-kit
cd publishing-kit/articles/<your-article>
```

One directory per article, holding the source markdown, the covers, the evidence files and the
generated `medium/` build. The pre-flight resolves paths against that directory and the Medium
image URLs are derived from its name, so the layout is load-bearing.

## The Source Article Is the dev.to One

dev.to is the source format, not one of three copies. It is the only destination where tables,
fenced code and emoji all render natively, so the other two artifacts are derived from it by
subtraction. Medium loses its tables to images. Builder Center loses its emoji and its
hard-wrapping.

```yaml
---
title: "Getting 23 KB of Markdown Into AWS Builder Center Without Touching the Clipboard"
published: false
description: "..."
tags: aws, ai, writing, devtools
cover_image: https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/publishing-kit-skill/devto-cover-aws.3ca0b7f4.jpg
---
```

`published: false`, always. dev.to keeps the first four tags and drops the rest, measured
2026-08-30, so a fifth tag is not an error.

## Every Article Needs a Cover, and the Two Sizes Disagree

There is no path where skipping the cover is correct, and nothing fails locally when you skip
it. dev.to fetches `cover_image:` at render time, so a missing file is invisible until it is a
broken image on a public post.

| Property | dev.to | AWS Builder Center |
| --- | --- | --- |
| Size | 1376x578 | 1200x675, 2 MB cap |
| Delivery | `cover_image:` URL | uploaded in the editor |
| Text in the image | fine | not recommended |

```shell
python3 scripts/make-cover.py --out devto-cover-aws.jpg --mode devto \
  --eyebrow "AWS BUILDER CENTER - DEV.TO - MEDIUM" \
  --headline "The paste that drops|every image, silently." \
  "--tile=-embed.html|base64 data: URIs|0 of 4|images survive the paste|SILENT FAILURE|orange" \
  "--tile=-hosted.html|real https:// URLs|4 of 4|images survive the paste|USE THIS ONE|blue"

python3 scripts/make-cover.py --out builder-cover.jpg --mode builder --ratio 4:5 \
  --content-address
```

```plaintext
wrote devto-cover-aws.3ca0b7f4.jpg  1376x578   85 KB
wrote builder-cover.2b7f0305.jpg    1200x675   15 KB
```

**Name the cover by a hash of its bytes.** MEASURED 2026-08-31: dev.to does not
re-host a cover, it proxies it, with your URL embedded in theirs —
`media2.dev.to/dynamic/image/.../https%3A%2F%2Fraw.githubusercontent.com%2F...`.
The URL you hand it is load-bearing for the life of the post, and a proxy keyed on
that URL decides when to look again. Regenerating a cover in place leaves two
images behind one address; reusing a filename across articles repaints the older
one. `--content-address` makes every regenerated cover a URL nothing has cached,
and leaves the old file in place so published articles keep rendering.

`--mode builder` defaults to text-free, following the editor's own guidance, and warns above the
2 MB cap.

Note the `--tile=` spelling. A tile whose first field begins with a hyphen is read by `argparse`
as an option name:

```plaintext
make-cover.py: error: argument --tile: expected one argument
```

Then open the file. A palette validator checks colour, not layout, and the first pass usually
has a label collision.

## No Number Ships Without an Artifact

Never restate a figure from prose. Not from another article, not from a code comment, not from a
chat log. **Prose is not evidence.**

```shell
python3 scripts/check-facts.py devto-publishing-kit-aws.md --evidence evidence/
```

```plaintext
devto-publishing-kit-aws.md: 4 claim(s) against 8 evidence file(s)

  ok    version      12.3.0                       <- environment.txt
  ok    quantity     150 tokens                   <- skill-footprint.txt
  ok    version      2.1.251                      <- environment.txt
  ok    version      3.13.14                      <- environment.txt

4 traced, 0 untraced
```

It traces prices, measurements, quantities, versions, cloud identifiers, digests, arch strings
and capacities, and reports which appear in no evidence file. It cannot tell you a number is
true. It tells you which numbers you are asserting without an artifact.

**Four claims out of a 23 KB article is not a green light.** Fenced code is stripped before
extraction, because pasted tool output is itself evidence, and this article keeps most of its
numbers in exactly that position. The tool covers the shapes it covers. The rest is traced by
hand and archived beside the article.

Scope `--evidence` to text files. It compares on digits alone, so a run directory of compressed
traces and protobufs matches claims against binary noise. One pass on an earlier article
reported 15 traced and 0 untraced; re-run against only the markdown, JSON and text artifacts it
became 14 traced and 1 untraced, and that one was a real drifted figure with no artifact
anywhere.

Two things the script does not do. **Check vendor and identity claims, not just numbers** —
archiving the EC2 instance-type data for one article surfaced two instance families described
with the wrong host CPU vendor throughout, which prose review had not caught. And **re-read
every comparison for what varied**, then say it once in a scope paragraph at the end.

## Pre-flight, and Let It Fail

```shell
python3 scripts/check-article.py devto-publishing-kit-aws.md --repo-root ../..
```

```plaintext
  ok    cover present: devto-cover-aws.jpg
  FAIL  devto-cover-aws.jpg is not committed -- the URL is fetched at render
        time, so it must be pushed before publishing
  ok    geometry 1376x578 is dev.to's displayed 2.381:1
  ok    published: false
  ok    title present
  ok    description present
  ok    tags present
  ok    devto-publishing-kit-gde-hosted.html image URLs resolve to publishing-kit-skill
  FAIL  6 medium/img image(s) not committed
  ok    no empty link targets

2 fail, 0 warn
```

Eight checks, ordered by how silently each one fails. The cover exists, `cover_image:`
references it, it is committed, the geometry matches, `published:` is false, the front matter is
complete, the Medium artifacts point at this article's directory, and no link target is empty.
It exits non-zero.

**A cover that exists on your disk and not in the remote is a cover dev.to cannot fetch**, and
the post is public by the time that shows up.

One gap to know about. Check 7 compares only the last path segment of the image URLs against the
article's directory name. A URL pointing at the right directory name in the wrong repository
passes it, which is the failure the next section walks into.

## Deploy to dev.to Over the API

dev.to has a REST API, and the front matter is part of the payload. Read it back off a published
article and the front matter is still there, inside `body_markdown`:

```plaintext
---
title: "The Cheapest CUDA GPU on AWS Has an Arm CPU — and You Probably Want the Intel One"
published: true
tags: aws, vllm, cuda, machinelearning
cover_image: https://raw.githubusercontent.com/xbill9/gemma4-dev/main/gpu-vllm-g4dn-2b/devto-cover.jpg
---
```

Title, tags and cover transfer with the body. Nothing is retyped, no cover is uploaded by hand,
and no browser is opened.

```shell
curl -s -X POST https://dev.to/api/articles \
  -H "api-key: $(cat ~/.devto.key)" -H "Content-Type: application/json" \
  -d @payload.json
```

A `PUT` to `/api/articles/<id>` overwrites in place. It does not change the slug of an
already-published article, measured 2026-08-30, so links already handed out survive an edit.

**A draft is never byte-identical to its source.** dev.to labels bare fences with a detected
language on the way in. Read back, that same published article has 23 opening fences and not one
of them is bare:

```plaintext
opening fences: 23  closing fences: 23
bare (unlabelled) opening fences: 0
{'```plaintext': 14, '```shell': 6, '```markdown': 1, '```yaml': 1, '```diff': 1}
```

Diff below that substitution before concluding the upload drifted.

## Route the Article to an Organization

The community channel, `dev.to/aws-builders/<slug>` rather than `dev.to/<user>/<slug>`, is an
API field and not an editor dropdown:

```shell
curl -s https://dev.to/api/organizations/aws-builders
```

```json
{ "type_of": "organization", "id": 2794, "username": "aws-builders",
  "name": "AWS Community Builders " }
```

```shell
curl -s -X PUT https://dev.to/api/articles/<id> -H "api-key: $KEY" \
  -H "Content-Type: application/json" -d '{"article":{"organization_id":2794}}'
```

There is no endpoint that lists your organizations. Recover them from the back catalogue, where
every article that has one carries an `organization` object:

```plaintext
articles listed: 40
  gde: 24
  aws-builders: 13
  None: 3
```

That also recovers the routing convention from the catalogue itself. A later update from source
does not clear the field, measured 2026-08-30, and the old URL keeps resolving after the move.

**Read article state from the listing, not from the by-id endpoint.**
`GET /api/articles/<id>` returned `{"error":"not found","status":404}` for one of three
published articles fetched by id during this run, with a valid key, while the same article sat
in `/api/articles/me` the whole time.

## Deploy to AWS Builder Center

New article is **"+" in the top bar → Article**. Do not open an existing draft's preview and
edit that.

Title and Description are ordinary inputs, 255 and 512 characters. Click and type. The cover
uploads through a real `<input type=file>`: locate it and drive it with an upload tool. **Never
click a file input** — that opens a native picker you cannot see.

The body is 22.7 KB of markdown that has to reach a `contenteditable`, and three obvious routes
are closed:

| Route | What happens |
| --- | --- |
| Cross-origin `fetch` into the editor page | CSP `connect-src`. A CORS header does not help, and the failure is an identical bare "Failed to fetch" either way |
| `file://` navigation | blocked by the browser extension |
| `wl-copy` / `xclip` | both hang the shell holding the selection, even detached with `setsid` or `nohup` |

**The system clipboard is not a fourth route, it is a hazard.** It is shared with whoever else
is at the machine. A synthetic Ctrl+C loses the race silently and Ctrl+V pastes their content
into your draft. Your Ctrl+C clobbers what they had copied, which is the more expensive half.
Measured 2026-08-30: another article landed in a draft twice, and nothing anywhere reported a
failed copy.

## The Route That Works

Fully automated, self-verifying, no clipboard.

**1. Inject the text in chunks through the JS bridge**, JSON-escaped so you control the
escaping, appending to one variable and checking the cumulative length after every chunk:

```js
window.__p = (window.__p || "") + "<json-escaped chunk>";
window.__p.length            // must equal the expected running total
```

About 1400 characters per chunk. A mismatch means characters were dropped. Redo that chunk, and
never proceed past one. Hand-transcribed base64 through the same bridge lost 40 characters out
of 3,192 on an earlier run, and base64 fails the decode rather than degrading.

**2. Checksum the whole payload before using it**, in the page, against the same computed
locally. Use a numeric checksum. A hex or base64 SHA can be redacted in transit and tell you
nothing:

```js
let a=0,b=0;
for(let i=0;i<window.__p.length;i++){a=(a+window.__p.charCodeAt(i))%65521;b=(b+a)%65521;}
({chars:window.__p.length, adler_a:a, adler_b:b})
```

**3. Clear the editor with the keyboard.** `document.execCommand("delete")` over a selected
range silently does nothing here and the paste then appends. You get the entire article twice,
and only a landmark count catches it. Click the body, Ctrl+A, Delete.

**4. Assert the editor is empty, then dispatch the paste.** The assertion is what prevents the
duplicate:

```js
const ed = document.querySelector('[contenteditable="true"]');
if (ed.innerText.length > 50) throw new Error("not empty, refusing to paste");
ed.focus();
const dt = new DataTransfer();
dt.setData("text/plain", window.__p);
ed.dispatchEvent(new ClipboardEvent("paste", {clipboardData: dt, bubbles: true, cancelable: true}));
```

**5. Count landmarks.** The opening sentence, the summary heading and the closing line, each
exactly once.

`dispatchEvent` returns `false`. That is `preventDefault`, not refusal. **Judge by the landmark
count, never by the return value.** The editor autosaves, with a saving indicator and no save
button.

## Unwrap the Paragraphs First

Builder Center's paste handler preserves the source's newlines inside a paragraph. Markdown
folds a single newline into a space and this editor does not, so a file hard-wrapped at 95
columns renders with a ragged break every 95 characters. It is visible only once published.

```shell
python3 scripts/serve-body.py builder-publishing-kit.md
```

```plaintext
chars : 23245
lines : 531 before unwrap, 411 after
```

It serves the body on `http://127.0.0.1`, unwrapped, leaving code, tables, lists and headings
alone, and prints a checksum. It also strips the title and the `*Subtitle:*` line, because those
are separate fields. Doing that by hand needs care with the line numbering — line 2 is the blank
line after the title, so `sed '1,2d'` takes the title and the blank and leaves the subtitle:

```plaintext
$ sed '1,2d' builder-publishing-kit.md | head -1
*Subtitle: A step by step publishing pipeline for AWS Builder Center...
```

Two more rules, both measured 2026-08-30. Tags are a fixed searchable vocabulary, five maximum:
`amazon-ec2`, `generative-ai` and `cost-optimization` exist, `gpu` does not, and neither does a
usable `inference`. And keep tables to about five columns, because seven get squeezed until
cells break mid-token.

## Editing After Publishing

Go to the published URL and use the **"..." menu on the article itself → Edit**. Do not navigate
to `/create/content/<id>`. That silently creates a new empty draft rather than editing the
existing piece.

## Derive the Medium Version Last

Medium's importer strips markdown tables entirely and flattens `<pre>` to a single line, so
nothing that depends on alignment survives as text. **Do not hand-write this file.**

```shell
python3 scripts/make-medium.py devto-publishing-kit-gde.md medium \
  --cover=devto-cover-gde.jpg \
  --img-base=https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/publishing-kit-skill/medium/img/
```

```plaintext
devto-publishing-kit-gde.md: 5 tables, 1 diagrams
   USE THIS   -> medium/devto-publishing-kit-gde-hosted.html
   not this   -> medium/devto-publishing-kit-gde-embed.html   (473 KB; data: URIs)
```

Paste the hosted variant, never the embed one. The embed variant inlines its images as base64
and Medium strips `data:` URIs on paste: 0 of 4 images survived from embed against 4 of 4 from
real URLs, measured 2026-08-30.

**Both flags are required, and neither failure is visible in the output.** With no `--cover`,
the script falls back to the first `*cover*.{jpg,png}` alphabetically, skipping builder-named
ones. Run against the GDE version of this article with no flag, it picked `devto-cover-aws.jpg`
— the AWS cover on the GDE story — and the first body image becomes Medium's cover. With no
`--img-base`, it derives one from a hardcoded repository and the article directory's last path
segment:

```plaintext
https://raw.githubusercontent.com/xbill9/gemma4-dev/main/publishing-kit-skill/medium/img/
```

Wrong repository, and the `articles/` segment is gone. Every `<img>` 404s, the embed variant
hides it because its images are inlined, and check 7 of the pre-flight passes because the last
segment still reads `publishing-kit-skill`.

## Announcing It on LinkedIn

LinkedIn is the fourth destination, and it sits between the other two cases. It **does** have an
API — `POST /rest/posts`, self-serve through the "Share on LinkedIn" product, `w_member_social`,
150 requests per member per day. But `lifecycleState` accepts only `PUBLISHED` on creation, so
posting through the API *is* publishing. There is no `published: false`.

```shell
python3 scripts/make-linkedin.py devto-publishing-kit-aws.md --api
```

```plaintext
  FAIL  4 link(s) still PENDING: builder, devto-aws, devto-gde, medium
  ok    hook fits the fold: 80 chars
  ok    post is 1269 chars of 3000
  ok    no markdown left; LinkedIn renders none of it
  ok    no Unicode pseudo-bold
```

So the artifact is a text file for the composer, which does have drafts. The generator writes it
and never posts. A `PENDING` link is written into the file as a visible placeholder **and** fails
the run, because the one thing an announcement post must do is resolve.

**LinkedIn renders no markup at all.** The `commentary` field is LinkedIn's `little` format,
whose entire element set is text, mentions and hashtags — no bold, no italics, no lists, no link
markup. And for the API only, every reserved character has to be backslash-escaped whether or not
it is used as markup: `|  {  }  @  [  ]  (  )  <  >  #  \  *  _  ~`. An article body is full of
them. `--api` writes that variant beside the plain one.

## Summary

The goal of this article was to publish one technical article to three destinations without
publishing three broken pages. The key to the solution was treating dev.to as the source format
and deriving the others from it, then refusing to ship on two checks that exit non-zero. The
measured results were:

- **dev.to needs no browser, because it has a complete REST API.** The front matter rides
  inside `body_markdown`, and `organization_id` routes the article to a community channel: 2794
  for AWS Community Builders, 11939 for Google Developer Experts on this account.
- **Medium and Builder Center have no publishing API**, so both are reached by Claude Code
  driving Chrome. Every browser hazard here follows from that.
- **LinkedIn has an API that cannot draft**, so its artifact is a file for the composer.
- **Builder Center needs a browser and never the clipboard.** Chunked injection with a running
  length check, a numeric checksum, a keyboard clear, an emptiness assertion, and a landmark
  count. Cross-origin `fetch`, `file://` and `wl-copy` are all closed.
- **Medium needs the hosted build**, 0 of 4 images surviving from the embed variant against 4 of
  4 from real URLs.
- **The covers are mandatory and differently sized**, 1376x578 at 84 KB by URL for dev.to and
  1200x675 at 15 KB uploaded and text-free for Builder Center.
- **The skill costs ~190 tokens resident** and ~9.5k when it fires, across 3,049 lines.
- **The pre-flight failed this article twice** before the artifacts were committed, which is
  what it is for.

Scope: one account, one run, on 2026-08-31, producing four artifacts from one source. Token
figures are Claude Code's own projections and not measured usage. The Medium importer
behaviours, the image survival counts, the clipboard incident, the base64 transcription loss,
the tag limits and the Builder Center field limits are carried from the kit's measurement log
dated 2026-08-23 and 2026-08-30 and were not re-measured here. Everything else was captured
during this run and archived beside the article, claim by claim, in `CLAIMS.md`.

The strategy for using a Claude Code skill for multi-destination technical publishing was
validated with an incremental step by step approach.

Any opinions in this article are those of the individual author and may not reflect the opinions of AWS.
