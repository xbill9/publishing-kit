# publishing-kit

A [Claude Code](https://claude.com/claude-code) skill and toolchain for publishing a
technical article to **AWS Builder Center**, **dev.to** and **Medium**, and
announcing it on **LinkedIn**.

Three destinations, three different artifacts — not three copies of one. They
disagree about tables, about code blocks, and about cover images, and **every
disagreement fails silently.** You get a plausible-looking file that the
destination quietly mangles, and you find out after publishing.

This packages the workarounds, the generators, and two checks that fail loudly
instead.

## Install

```
/plugin marketplace add xbill9/publishing-kit
/plugin install publishing
```

Or copy `skills/publishing/` into `~/.claude/skills/`.

## What it does

**Fails the build when a cover image is missing.** Every article needs one and
nothing errors locally without it — dev.to only fetches the `cover_image:` URL at
render time, so a missing or uncommitted file surfaces as a broken image on a
published post.

**Converts tables and code for Medium.** Medium's importer strips markdown tables
entirely and flattens `<pre>` to a single line. `make-medium.py` renders them to
PNG at 2x and emits a self-contained paste variant and a hosted import variant.

**Traces every factual claim to an artifact.** `check-facts.py` extracts prices,
measurements, versions and cloud identifiers, then reports which appear in no
evidence file you supplied. It cannot tell you a number is true — it tells you
which numbers you are asserting from memory.

## Scripts

| Script | Purpose |
|---|---|
| `preflight.py` | **Start here.** Runs every check for an article with one exit code. `--live` fetches every published URL and compares bytes. |
| `make-builder.py` | Derives the Builder Center version from the dev.to source: front matter and emoji out, title/subtitle and the AWS disclaimer in. Checks table width. |
| `check-links.py` | Fetches every cover and Medium image URL and compares the served bytes to disk. The only check that sees what a reader sees. |
| `check-article.py` | Pre-flight. Cover exists, is referenced, is **committed**, right geometry; `published: false`; front matter complete; Medium artifacts resolve to this article's directory. Exits non-zero. |
| `check-facts.py` | Fact-tracing against evidence files. Exits non-zero on untraced claims. `.factsignore` records deliberate exemptions with reasons. |
| `make-medium.py` | Tables and diagrams to PNG, emits `-embed.html` (paste) and `-hosted.html` (import). |
| `make-cover.py` | Cover images. `--mode devto` (1376x578, the 2.381:1 dev.to actually displays) and `--mode builder` (1200x675, text-free per AWS guidance). `--content-address` names the file by a hash of its bytes, because dev.to proxies the cover URL rather than re-hosting it. |
| `make-linkedin.py` | LinkedIn post draft with links. `--bullets-from` names the section its bullets come from. |

| `publish-devto.py` | Create, update, list and route dev.to articles over the REST API. Runs the pre-flight first and refuses on a FAIL. Key from `$DEV_TO_API_KEY` or `~/.devto.key`, never argv. |
| `bodytext.py` | Paragraph unwrapping, in one place. dev.to and Builder Center both render a hard-wrapped source with a break at every wrap. |
| `make-slack.py` | **Optional.** AWS Community Builders Slack announcement, in the author's own channel format. Fails on a PENDING or draft link, and on sending the GDE dev.to copy to an AWS channel. Does not post. |
| `make-gchat.py` | **Optional.** GDE Americas (Google Chat) announcement, the same shape as the Slack one. Leads with the `dev.to/gde` copy and fails on sending the aws-builders one to the Google community. Does not post. |
| `make-advocu.py` | **Optional, GDE only.** Prepares an Advocu activity sheet from a published article. Refuses a placeholder or draft URL. Reads the publication date from dev.to, and writes reach as a labelled standing estimate rather than a counter reading that would cover one destination of five. |
| `serve-body.py` | Serves an article body on localhost so a browser can copy it into a rich-text editor. Strips the title and subtitle, prints a checksum. |

## Typical run

```bash
python3 scripts/make-cover.py --out devto-cover.jpg --mode devto \
  --headline "Your headline|second line" \
  --tile "thing-a|subtitle|\$0.42|per hour|CHEAPEST PER HOUR|orange" \
  --tile "thing-b|subtitle|\$0.60|per M tokens|CHEAPEST PER TOKEN|blue"

python3 scripts/make-medium.py devto-article.md medium

python3 scripts/check-facts.py   devto-article.md --evidence run.json logs/
python3 scripts/check-article.py devto-article.md --repo-root .
```

Commit and push before publishing — the cover and the Medium images are fetched
by URL at render time.

## Two things this exists because of

**A fix that could not propagate.** `make-medium.py` had been copied into eight
projects across four variants. One variant hardcoded its own project path into the
image base URL, so a copy taken elsewhere pointed every `<img>` at another
project's URLs — all 404 — while the paste variant hid it completely because its
images are inlined. Five copies already had the fix. The one that got copied did
not. It is one script here.

**A body that would not paste.** Getting 15 KB of markdown into AWS Builder
Center's `contenteditable` defeated three obvious routes: cross-origin `fetch` is
blocked by CSP, `wl-copy`/`xclip` hang the shell holding the selection, and
hand-transcribed base64 through a JS bridge dropped 40 characters out of 3,192 —
which base64 fails on rather than degrades. What works is letting the browser copy
for itself: `serve-body.py` puts the text on localhost (`file://` is blocked by the
extension, `http://127.0.0.1` is not), and a real Ctrl+A/Ctrl+C/Ctrl+V transfers it
with no transcription at all.

**A wrong fact that survived proof-reading.** Archiving the EC2 instance-type data
as evidence for one article surfaced that two instance families had been described
with the wrong host CPU vendor throughout the piece. Prose review had not caught it;
producing the artifact did.

## Retargeting

Voice, section order, and the opener/closing formulas live in
`skills/publishing/references/house-style.md`. Swap that one file — nothing in
`SKILL.md` or `scripts/` depends on it.

## License

Apache-2.0
