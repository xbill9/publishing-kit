# Streamline Publishing with a Claude Code Skill

*Subtitle: A Claude Code skill that turns one markdown file into dev.to, AWS Builder Center, Medium and LinkedIn versions, checks them before they ship, and posts the ones with an API.*

> **TL;DR:** [publishing-kit](https://github.com/xbill9/publishing-kit) packages the whole
> publishing lifecycle as a Claude Code skill. Write one markdown file, and it builds the dev.to,
> AWS Builder Center, Medium and LinkedIn versions, checks them, and posts the ones that have an
> API. This article, its cover, and all five of its artifacts were produced by the thing the
> article is about — dogfooding all the way down. More on that at the end.

Publishing one technical article to four places involves a surprising amount of ceremony: making
a cover at whatever size each destination wants, rendering tables to images because Medium's
importer eats them, stripping emoji for AWS, checking that every number in the piece came from a
real run, getting 23 KB of markdown into a browser editor that has no API, remembering which
organization the article routes to, and writing the announcement post afterwards — by which
point you have four slightly different files and no idea which one is current.

I packaged all of that into **[publishing-kit](https://github.com/xbill9/publishing-kit)** — a
Claude Code skill and a dozen small scripts — so you can just ask Claude to publish.

## What it does

The skill teaches Claude the publishing lifecycle; the scripts do the parts a language model
should not be doing by hand.

- **Build the artifacts:** one source file becomes the dev.to markdown, the Builder Center
  version with emoji stripped and the AWS disclaimer appended, Medium HTML with every table
  rendered to a PNG, and a LinkedIn post. `make-builder.py`, `make-medium.py`,
  `make-linkedin.py`.
- **Make the cover once:** `make-cover.py --sizes devto,builder` renders one design at every
  geometry the destinations demand, names it by a hash of its own bytes, and tells you which type
  sizes survive a feed card. One article, one cover.
- **Trace every number:** `check-facts.py` pulls the prices, measurements and versions out of
  your prose and reports which ones appear in no evidence file. It cannot tell you a figure is
  true. It tells you which ones you are asserting from memory.
- **Pre-flight:** `preflight.py --live` runs the lot and exits non-zero — cover committed and
  matching HEAD, geometry right, front matter complete, no hard-wrapped paragraphs, and every
  published URL fetched and compared byte for byte against your disk.
- **Post where there is an API:** `publish-devto.py --create` takes the front matter as the
  payload, so title, tags and cover ride along with the body, and `--org-slug` routes it to a
  community channel. No browser.
- **Drive the editors that have none:** AWS Builder Center and Medium are Chrome work, and the
  skill knows the route — payload through `window.name`, a checksum on both sides, an emptiness
  assertion before the paste, and a landmark count after it.

It also encodes the hard-won details you would otherwise learn the day after publishing: that
dev.to renders markdown with hard breaks **on**, so a source wrapped at 95 columns arrives with a
stray break in every paragraph; that dev.to does not host your cover but proxies it at 2.381:1,
so a 16:9 cover loses 95px off the top and bottom; that Medium drops `data:` URI images on paste,
so the self-contained build arrives with no pictures at all; and that LinkedIn's Posts API cannot
create a draft, because `PUBLISHED` is the only state it accepts on creation.

## Install

The fastest path is the plugin marketplace:

```shell
/plugin marketplace add xbill9/publishing-kit
/plugin install publishing@publishing-kit
```

Prefer the classic route? Clone it and symlink the skill:

```bash
git clone https://github.com/xbill9/publishing-kit
ln -s "$PWD/publishing-kit/skills/publishing" ~/.claude/skills/publishing
```

You will need Python 3 with Pillow for the cover and table rendering, a dev.to API key in
`~/.devto.key`, and a public repo to hold the article directory — both the cover and the Medium
images are fetched by URL when the page renders, so unpushed means broken.

One thing worth knowing if you plan to hack on the skill itself: installing from the marketplace
takes a **snapshot**, and `claude plugin update` compares version strings, so edits under the
same version never reach your session. Symlink while you are iterating.

## What it looks like in practice

Once installed, you talk to Claude Code like this:

> "Write this benchmark up and publish it to dev.to under aws-builders"

Claude writes the source article, generates the cover at both geometries, traces the numbers
against your run artifacts, runs the pre-flight, tells you what failed, and — once it passes —
posts it as a draft and hands you the link. Then:

> "Now make the Medium and Builder Center versions"

It derives them, renders the tables to images, opens Chrome, and fills the editors. It stops at
draft on every destination and hands back links. Publishing is your keystroke, not its.

## Debugging a publish that went sideways

This is the half that surprised me most, and where most of the skill's value ended up.

**The page does not look like the file.** Fetch what the destination actually serves rather than
reasoning about what you pushed:

```shell
python3 scripts/check-links.py article.md --live
```

```plaintext
  ok    cover.b873c938.jpg: HTTP 200, bytes match disk
  FAIL  table-3.png: HTTP 200 but the served bytes differ from disk
```

That second line is a regenerated image that was never re-committed. Every other check in the kit
reasons about local state — is the file there, is it tracked — and each of those can pass while
the published URL serves something else.

**The paragraphs look ragged.** `check-article.py` reports hard-wrapped paragraphs with the line
number of the first one, and `publish-devto.py` unwraps on the way out so your repo copy stays
readable at 95 columns and the published page does not.

**An image is missing on Medium.** You pasted `-embed.html`. Paste `-hosted.html`, which
references real URLs Medium re-hosts, and commit the images first.

**A number in the article has no artifact behind it.** `check-facts.py` will name it. Every
untraced claim is one of three things: measured but never archived, arithmetic that should be
labelled as arithmetic, or asserted from memory — and it is always the third one that turns out
to be wrong.

## Under the hood

Twelve scripts, one `SKILL.md`, four reference files. The skill decides when each script runs;
the scripts are independently runnable and print what they did.

The bit worth stealing for your own skills is `references/house-style.md`. Voice, section order,
the opener and closing formulas live in that one file, and nothing in `SKILL.md` or the scripts
depends on it. Swap it and the kit writes as somebody else.

`skill-footprint.py` measures the skill's own size and token cost, and emits the cost table and
cover footer for articles like this one — because a figure that changes on every commit does not
belong in prose you have to remember to update.

## Dogfooding: this article, and its cover 🐕🍖

Every artifact here came out of the kit. The cover was rendered by `make-cover.py`, the Builder
Center version was derived by `make-builder.py`, the Medium build by `make-medium.py`, and the
dev.to draft posted by `publish-devto.py`.

The two numbers on the cover are real, and both were found by using the kit on itself:

| | measured |
| --- | --- |
| dev.to, hard-wrapped paragraphs | **47 of 62** in a published article carried a stray break |
| Medium, images pasted as data URIs | **0 of 4** survived; from real URLs, 4 of 4 |

The first one had been happening to my articles for months. The second cost a full re-do the
first time it happened. Neither is in the docs of either destination, and both are now checks.

The run also found five faults in the kit itself, which is the point of eating your own cooking:
`make-medium.py` had another project's repo hardcoded as its default image base;
`check-article.py` passed a cover that was tracked but regenerated; `make-cover.py` lost a `--tile`
value beginning with a hyphen to `argparse`; `check-facts.py` read `127.0.0.1` as a version
number; and the cost table in this very article drifted three times before it became generated
output.

## Links

- **Repo:** [github.com/xbill9/publishing-kit](https://github.com/xbill9/publishing-kit) (Apache-2.0)
- **The skill:** [`skills/publishing/SKILL.md`](https://github.com/xbill9/publishing-kit/blob/main/skills/publishing/SKILL.md)
- **This article's directory**, with every artifact and the evidence behind every number:
  [`articles/publishing-kit-skill/`](https://github.com/xbill9/publishing-kit/tree/main/articles/publishing-kit-skill)
- **Claude Code:** [claude.com/claude-code](https://claude.com/claude-code)

*Issues and PRs welcome. This is a third-party community project, not affiliated with dev.to,
Medium, AWS or LinkedIn — and the destination behaviours described here were measured on
2026-08-31, so check them again before you trust them.*

Any opinions in this article are those of the individual author and may not reflect the opinions of AWS.
