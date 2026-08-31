---
title: "One Article, Four Destinations: a Claude Code Skill That Fails the Build"
published: false
description: "Step-by-step: packaging a publishing workflow as a Claude Code skill — generating the cover, tracing every number to an artifact, building the Medium version, and posting over the dev.to API, with a pre-flight that exits non-zero."
tags: ai, devtools, writing, opensource
cover_image: https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/publishing-kit-skill/cover.d8d95a61.jpg
---

This tutorial walks through **publishing-kit**, a [Claude Code](https://claude.com/claude-code)
skill that turns one technical article into five publishable artifacts — dev.to, AWS Builder
Center and Medium — and refuses to ship the ones that are broken.

https://github.com/xbill9/publishing-kit

The example is a real one: this article. Every command below was run to produce the four
versions, and the numbers come out of that run, on 2026-08-31.

Follow along and you'll have a working skill, an article the destinations will not mangle, and
an evidence directory that says where every number came from.

---

#### Why a skill and not a checklist?

Because the failures are silent, and each one costs a re-publish.

Three claims about publishing that sound reasonable and are wrong, so nobody has to find out the
hard way:

| Claim | Why it fails |
| --- | --- |
| "One markdown file, three destinations" | tables and code survive on two of them and not on the third |
| "The self-contained HTML is the safe one" | Medium strips its `data:` images on paste, 0 of 4 surviving |
| "A missing cover is a local problem" | dev.to fetches the cover at render time, so it breaks in public |

That second row is the one that pays for the whole kit. The self-contained build inlines every
image as base64. Pasted into Medium, the cover and every table image disappear, with no error,
no placeholder and no broken-image icon. Measured 2026-08-30:

| Variant | Images in the file | Survive the paste |
| --- | --- | --- |
| `<slug>-embed.html` | 4, inlined as base64 | ❌ 0 of 4 |
| `<slug>-hosted.html` | 4, real `https://` URLs | ✅ 4 of 4 |

#### How does this all fit together?

One source article, three derived artifacts, two checks between them:

```plaintext
                       devto-<slug>.md   ← the source, dev.to flavour
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   make-cover.py        check-facts.py       check-article.py
   1376×578 dev.to      every claim with     cover, geometry,
   1200×675 builder     no artifact behind   published:false,
   text-free for AWS    it, listed           dead links
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
     dev.to API         make-medium.py        serve-body.py
     POST / PUT         tables → PNG at 2×    localhost → Builder
     organization_id    -hosted.html          Center contenteditable
     no browser         paste, never import   no clipboard, ever
```

A dozen scripts, one skill file, four reference files. The skill decides when each one runs.

#### One of them has an API. Two of them do not.

This is the split that shapes everything else:

| Destination | How the article gets there | Draft state |
| --- | --- | --- |
| **dev.to** | ✅ **full REST API** — create, update in place, list, set the org. No browser. | `published: false` |
| **Medium** | ❌ no API. **Claude Code driving Chrome**, pasting into the editor. | editor draft |
| **AWS Builder Center** | ❌ no API. **Claude Code driving Chrome**, injecting into a `contenteditable`. | autosaved draft |
| **LinkedIn** | ⚠️ API exists, but creation only accepts `PUBLISHED` — posting *is* publishing. | composer only |

The browser work in Step 9 is not a shortcut taken instead of reading API docs. **For Medium and
Builder Center there is no API to read.** The clipboard races, the duplicate pastes and the
silently stripped images are all the price of that one row.

And the rule that falls out of it: **before reaching for the browser on any destination, check
whether it has an API.** dev.to's was sitting unused in eight directories while a whole browser
flow was built around it.

#### What is a Claude Code skill, in one paragraph?

A directory with a `SKILL.md` in it. The YAML front matter carries a name and a description; the
body carries the instructions. The description is loaded into every session and the body is read
only when the description matches what you asked for, which makes the description the part you
tune and the body the part you fill.

#### Step 1 — Install it

The kit ships as a plugin marketplace, so there is no file copying:

```shell
claude plugin marketplace add /home/xbill/publishing-kit
claude plugin install publishing@publishing-kit
```

```plaintext
✅ Successfully added marketplace: publishing-kit (declared in user settings)
✅ Successfully installed plugin: publishing@publishing-kit (scope: user)
```

That is a local checkout. `xbill9/publishing-kit` works the same way — main serves the
marketplace manifest, verified HTTP 200. Restart the session, then read what it costs:

```shell
claude plugin details publishing
```

```plaintext
Projected token cost
  Always-on:   ~190 tok   added to every session

  component   always-on  on-invoke
  publishing       ~190     ~10.6k
```

**That split is the design.** The 528 character description is the resident cost. The 526 line
`SKILL.md` is the on-invoke cost.

#### 🔎 Tip: if you are developing the skill, do not install it

Installing from a local path takes a snapshot. It does not link the working tree:

```shell
stat -c '%d:%i  %n' skills/publishing/SKILL.md \
  ~/.claude/plugins/cache/publishing-kit/publishing/0.6.0/skills/publishing/SKILL.md
```

```plaintext
21:7596109  /home/xbill/publishing-kit/skills/publishing/SKILL.md
21:7623871  /home/xbill/.claude/plugins/cache/.../skills/publishing/SKILL.md
```

Different inodes. A line appended to the worktree copy does not appear in the installed one, and
`installed_plugins.json` records the commit it was pinned at. Edits arrive after
`claude plugin marketplace update` and `claude plugin update`, and not before. While iterating,
symlink the skill into `~/.claude/skills/` instead.

#### Step 2 — Write the dev.to source

dev.to is the source format, not one of three copies. It is the only destination where tables,
fenced code and emoji all render natively, so the other artifacts are derived from it by
subtraction.

```yaml
---
title: "One Article, Four Destinations: a Claude Code Skill That Fails the Build"
published: false
description: "Step-by-step: packaging a publishing workflow as a Claude Code skill..."
tags: ai, devtools, writing, opensource
cover_image: https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/publishing-kit-skill/cover.d8d95a61.jpg
---
```

`published: false`, always, and let the pre-flight enforce it. dev.to keeps the first four tags
and drops the rest, measured 2026-08-30.

#### Step 3 — Make the cover

There is no path where skipping it is correct, and nothing fails locally when you skip it.
dev.to fetches `cover_image:` when it renders the published page.

| | dev.to | AWS Builder Center |
| --- | --- | --- |
| Size | **1376x578** | **1200x675**, 2 MB cap |
| Delivery | `cover_image:` URL | uploaded in the editor |
| Text in the image | fine | not recommended |

```shell
BASE=https://raw.githubusercontent.com/<u>/<repo>/main/<dir>

python3 scripts/make-cover.py --out cover.jpg --sizes devto,builder --flow \
  --content-address --url-base "$BASE" \
  --eyebrow "PUBLISHING-KIT - A CLAUDE CODE SKILL" \
  --headline "One source. Four destinations." \
  --subhead "Two have a REST API. Two have none." \
  --source "devto-article.md|the source, dev.to flavour" \
  --step "check-facts.py" --step "check-article.py" --step "make-medium.py" \
  --dest "dev.to — Google Developer Experts|REST API, no browser|blue" \
  --dest "AWS Builder Center|no API — Chrome, no clipboard|orange" \
  --dest "Medium|no API — paste the hosted build|orange" \
  --dest "LinkedIn|API cannot draft — a file|muted" \
  --legend "REST API|blue, browser required|orange, no draft state|muted"
```

```plaintext
wrote cover.d8d95a61.jpg           1376x578   79 KB
wrote cover-builder.92fa3743.jpg   1200x675   67 KB
```

**`--content-address` names the file by a hash of its own bytes, and it is not
optional once an article is published.** dev.to does not re-host your cover — it
*proxies* it, with your URL embedded in theirs:

```plaintext
https://media2.dev.to/dynamic/image/width=1000,height=420,fit=cover,gravity=auto,
  format=auto/https%3A%2F%2Fraw.githubusercontent.com%2F...%2Fdevto-cover.jpg
```

So the URL you hand it stays load-bearing for the life of the post, and a proxy
keyed on that URL decides for itself when to look again. Regenerate a cover in
place and you get an article whose cover may or may not be the one you just made;
reuse a filename across articles and the older one silently repaints. A hashed
name is a URL nothing has cached, and the old file stays where it is so published
articles keep rendering. It is the same reasoning the Medium importer forced —
that cache is keyed on URL too, and `?v=2` does not bust it.

`--mode builder` defaults to text-free, following AWS's own guidance. Then open the file. A
palette validator checks colour, not layout, and the first pass usually has a label collision.

**`--sizes devto,builder` renders ONE design at both geometries.** An article published to
four destinations is one piece and wants one cover; giving each destination its own picture is
three things to keep in step instead of one, and it is exactly what leaves a directory holding
several `*cover*.jpg` for the alphabetical `--cover` fallback to pick wrongly from. The
pre-flight now fails when sibling versions reference different covers, which is the check that
was missing while this article shipped three of them.

**`--flow` draws the pipeline instead of stat tiles, and that is a deliberate downgrade of the
numbers.** The first cover for this article showed the skill's token cost on two big tiles —
accurate, and a detail from the middle of the piece rather than its subject. The subject is the
shape: one source, a set of checks, and destinations that disagree. Colour carries the one thing
worth seeing at a glance and nothing decorative — **blue reaches over an API, orange needs a
browser driven for it.**

#### 🔎 Tip: tiles that begin with a hyphen

`--tile "-embed.html|..."` does not reach the script. `argparse` reads the value as an option
name:

```plaintext
make-cover.py: error: argument --tile: expected one argument
```

Use `--tile=-embed.html|...` with an equals sign.

#### Step 4 — Trace every number to an artifact

Never restate a figure from prose. Not from another article, not from a code comment, not from a
chat log. **Prose is not evidence.**

```shell
python3 scripts/check-facts.py devto-publishing-kit-gde.md --evidence evidence/
```

```plaintext
devto-publishing-kit-gde.md: 4 claim(s) against 8 evidence file(s)

  ok    version      0.6.0                        <- install-is-a-snapshot.txt
  ok    version      12.3.0                       <- environment.txt
  ok    version      2.1.251                      <- environment.txt
  ok    version      3.13.14                      <- environment.txt

4 traced, 0 untraced
```

It traces prices, measurements, quantities, versions, cloud identifiers, digests, arch strings
and capacities. It cannot tell you a number is true. It tells you which numbers you are
asserting without an artifact.

**Four claims out of a full-length article is not a green light.** Fenced code is stripped before
extraction, because pasted tool output is itself evidence, and this article keeps most of its
numbers there. Trace the rest by hand and archive it. The ledger for this article is
`CLAIMS.md`, and it sorts every claim into measured-on-this-run, read-from-the-source,
or carried-from-the-log-with-a-date.

Every untraced claim is one of three things:

1. **Measured, but the artifact was never archived.** Archive it. If the machine is gone, save
   the captured output verbatim with a header saying where and when it came from.
2. **Arithmetic.** Legitimate. Label it as arithmetic and record the derivation.
3. **Asserted from memory.** Go and measure it, or cut it.

Scope `--evidence` to text files. It compares on digits alone, so a directory of compressed
traces and protobufs matches claims against binary noise.

#### Step 5 — Pre-flight

```shell
python3 scripts/check-article.py devto-publishing-kit-gde.md --repo-root ../..
```

```plaintext
  ok    cover present: devto-cover-gde.jpg
  FAIL  devto-cover-gde.jpg is not committed -- the URL is fetched at render
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

Eight checks, ordered by how silently each one fails, and it exits non-zero. **A cover that
exists on your disk and not in the remote is a cover dev.to cannot fetch**, and the post is
public by the time that shows up.

One gap. Check 7 compares only the last path segment of the image URLs against the article's
directory name, so a URL with the right directory name in the wrong repository passes.

#### Step 6 — Build the Medium artifact

Medium's importer strips markdown tables entirely and flattens `<pre>` to a single line while
dropping `<br>`. **Do not hand-write this file.**

```shell
python3 scripts/make-medium.py devto-publishing-kit-gde.md medium \
  --cover=devto-cover-gde.jpg \
  --img-base=https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/publishing-kit-skill/medium/img/
```

```plaintext
devto-publishing-kit-gde.md: 5 tables, 1 diagrams
   USE THIS   -> medium/devto-publishing-kit-gde-hosted.html
   not this   -> medium/devto-publishing-kit-gde-embed.html   (473 KB; data: URIs)
   Medium never fills its Title field from pasted content -- set the title separately.
```

Every table and box-drawing diagram becomes a PNG at 2x. Pasting the hosted file beats importing
it, because the `<pre>` flattening is an importer behaviour and not an editor one, so multi-line
code survives a paste with its highlighting. The images have to be committed and pushed first.

Both flags are required, and neither failure is visible in the output:

- **`--cover=`.** Without it the script falls back to the first `*cover*.{jpg,png}`
  alphabetically, skipping builder-named ones. Run against this article with no flag, it picked
  `devto-cover-aws.jpg` — the AWS cover on the GDE story. The first body image becomes Medium's
  cover, so that is the art that ships.
- **`--img-base=`.** Without it the script derives one from a hardcoded repository and the
  article directory's last path segment, which here resolved to
  `.../gemma4-dev/main/publishing-kit-skill/medium/img/`. Wrong repository, `articles/` dropped,
  every `<img>` 404. The embed variant hides it completely, because its images are inlined.

Two more, both measured 2026-08-30. **The title never transfers** — type it in by hand. And
**`#` and `##` both render at Medium's title size**, so the generator demotes headings; this
article came out as one `<h1>` and 14 `<h4>`. A fork of the generator that borrowed only the
table rendering once shipped a story with 19 `<h2>` in it.

#### Step 7 — Post over the dev.to API

The front matter is part of the payload. Read a published article back and it is still there,
inside `body_markdown`:

```plaintext
---
title: "The Cheapest CUDA GPU on AWS Has an Arm CPU — and You Probably Want the Intel One"
published: true
tags: aws, vllm, cuda, machinelearning
cover_image: https://raw.githubusercontent.com/xbill9/gemma4-dev/main/gpu-vllm-g4dn-2b/devto-cover.jpg
---
```

Title, tags and cover transfer with the body, so nothing is retyped and no cover is uploaded by
hand.

```shell
curl -s -X POST https://dev.to/api/articles \
  -H "api-key: $(cat ~/.devto.key)" -H "Content-Type: application/json" \
  -d @payload.json
```

A `PUT` to `/api/articles/<id>` overwrites in place and does not change the slug of an
already-published article, measured 2026-08-30.

**A draft is never byte-identical to its source.** dev.to labels bare fences with a detected
language on the way in — read back, that published article has 23 opening fences and none of
them bare:

```plaintext
opening fences: 23  closing fences: 23
bare (unlabelled) opening fences: 0
{'```plaintext': 14, '```shell': 6, '```markdown': 1, '```yaml': 1, '```diff': 1}
```

#### Step 8 — Route it to an organization

The community channel is an API field, not an editor dropdown:

```shell
curl -s https://dev.to/api/organizations/gde
```

```json
{ "type_of": "organization", "id": 11939, "username": "gde",
  "name": "Google Developer Experts" }
```

```shell
curl -s -X PUT https://dev.to/api/articles/<id> -H "api-key: $KEY" \
  -H "Content-Type: application/json" -d '{"article":{"organization_id":11939}}'
```

There is no endpoint that lists your organizations. Recover them from the back catalogue, where
every article that has one carries an `organization` object:

```plaintext
articles listed: 40
  gde: 24
  aws-builders: 13
  None: 3
```

**Read article state from the listing, not from the by-id endpoint.**
`GET /api/articles/<id>` returned `{"error":"not found","status":404}` for one of three
published articles fetched by id during this run, with a valid key, while the same article sat
in `/api/articles/me` the whole time.

#### Step 9 — Builder Center, without the clipboard

Builder Center has no API, so this one is a browser flow.

**The system clipboard is shared with whoever else is at the machine.** A synthetic Ctrl+C loses
the race silently and Ctrl+V pastes their content into your draft, while your Ctrl+C clobbers
what they had copied. Measured 2026-08-30: another article landed in a draft twice, and nothing
reported a failed copy.

The route that works: inject the body in ~1400 character JSON-escaped chunks through a JS
bridge, checking the cumulative length after each one; checksum the payload in the page against
the same computed locally, numerically, because a hex digest can be redacted in transit; clear
the editor with a real Ctrl+A and Delete, because `execCommand("delete")` no-ops there and the
paste then appends the whole article a second time; assert the editor is empty; dispatch a
`paste` event with a `DataTransfer`; then count landmarks. `dispatchEvent` returns `false`, which
is `preventDefault` and not refusal.

Cross-origin `fetch` is blocked by CSP, `file://` is blocked by the extension, and `wl-copy` and
`xclip` both hang the shell holding the selection. Those three are closed.

One formatting rule that only appears after publishing: **Builder Center preserves the source's
newlines inside a paragraph.** A file hard-wrapped at 95 columns renders with a ragged break
every 95 characters.

```shell
python3 scripts/serve-body.py builder-publishing-kit.md
```

```plaintext
chars : 23234
lines : 531 before unwrap, 411 after
```

Code, tables, lists and headings are left alone.

#### Step 10 — Announce it on LinkedIn

LinkedIn is the fourth destination and it sits between the other two cases. It **does** have an
API — `POST /rest/posts`, self-serve via the "Share on LinkedIn" product, `w_member_social`, 150
requests per member per day. But `lifecycleState` accepts only `PUBLISHED` on creation, so
posting through it *is* publishing. There is no `published: false` here.

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

The artifact is a text file for the composer, which does have drafts, and the generator never
posts. A `PENDING` link lands in the file as a visible placeholder **and** fails the run: an
announcement whose links do not resolve is worse than no announcement.

**LinkedIn renders no markup at all.** Post text is the `commentary` field in LinkedIn's `little`
format, and its entire element set is text, mentions and hashtags. No bold, no italics, no lists,
no link markup. For the API only, every reserved character must be backslash-escaped whether or
not it is used as markup, and an article body is full of them. `--api` writes that variant
alongside.

🔎 **Do not reach for Unicode pseudo-bold.** Having no bold, the usual workaround is the
Mathematical Alphanumeric Symbols block. A screen reader announces those code points one at a
time or skips them, so the headline becomes the least readable part of the post. The generator
fails the run if any appear.

#### What it costs to carry

| Component | Lines |
| --- | --- |
| `SKILL.md` | 578 |
| `references/browser-publishing.md` | 309 |
| `references/house-style.md` | 81 |
| `references/linkedin.md` | 148 |
| `references/medium.md` | 119 |
| `templates/linkedin-post.txt` | 9 |
| 12 scripts | 2,493 |
| **total** | **3,737** |

Of which ~190 tokens are resident in every session and ~10.6k load when the skill fires.

#### So, worth it?

For one article, no. The kit is worth its 3,737 lines at the point where the same failure has
cost you twice, because every failure in it is one that produced a plausible-looking file and a
broken published page.

The `house-style.md` split is the part worth copying. Voice, section order, the opener and the
closing formulas live in that one file, and nothing in `SKILL.md` or the scripts depends on it.
Swap it and the kit writes as someone else.

#### Cheat sheet

```shell
# install
claude plugin marketplace add xbill9/publishing-kit
claude plugin install publishing@publishing-kit

# build
python3 scripts/make-cover.py  --out devto-cover.jpg --mode devto --headline "a|b"
python3 scripts/make-cover.py  --out builder-cover.jpg --mode builder --ratio 4:5
python3 scripts/make-medium.py devto-article.md medium \
  --cover=devto-cover.jpg --img-base=https://raw.githubusercontent.com/<u>/<repo>/main/<dir>/medium/img/

# refuse to ship
python3 scripts/check-facts.py   devto-article.md --evidence evidence/
python3 scripts/check-article.py devto-article.md --repo-root .
python3 scripts/make-linkedin.py devto-article.md --api

# commit and push BEFORE publishing: the cover and the Medium images are fetched by URL
git add -A && git commit -m "article" && git push
```

Five rules to remember: **dev.to is the source** and the only one with a real API, **Medium and
Builder Center are browser work** because they have none, every article has a **cover**, Medium
gets **`-hosted.html`** and never the embed, and **no number ships without an artifact**.

---

*publishing-kit 0.6.0, Claude Code 2.1.251, Python 3.13.14, Pillow 12.3.0, on Linux x86_64.
Token costs are Claude Code's own projections, not measured usage. The Medium importer
behaviours, the image survival counts, the clipboard incident and the tag limits are carried
from the kit's measurement log dated 2026-08-23 and 2026-08-30 and were not re-measured here.
Everything else was captured on the 2026-08-31 run that produced these four versions, and is
archived claim by claim in `CLAIMS.md`.*

The strategy for using a Claude Code skill for multi-destination technical publishing was
validated with an incremental step by step approach.
