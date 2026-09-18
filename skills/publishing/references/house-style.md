# House style

**Swap this one file to retarget the skill to a different author or publication.**
Nothing else in `SKILL.md` or `scripts/` depends on it.

## Voice

Declarative technical prose. Short paragraphs, two to four sentences. Present
tense. Bold used sparingly, for file names and conclusions. **Command, then its
output**, throughout — never a command without what it printed.

Sections are short and numerous, twenty or more, in **lifecycle order**:

> environment setup → MCP server over stdio → deploy → validate → benchmark
> sweep → compare to other deployments → cost → teardown → summary

That order is the point. It stops a validation pass ending at "the model
answered."

## Prose: what the author has had to correct, repeatedly

These were corrected in four sessions running, each time after an article was
drafted. `check-prose.py` enforces the list at the bottom of this section, and
`preflight.py` fails on it. Read this **before** drafting, not after.

**1. Report the finding, never the work.** No drafts, no bugs found, no discarded
runs, no "the first version", no "what it cost to get here". A method rule is
stated as a property of the method ("both clients get the same token"), never as
the story of the run that lacked it. Harness bugs belong in commit messages and
plan files. The author: *"the finding is the focus not your fumbles."*

**2. No rhetorical contrast or reveal lines.** State the positive fact.

| do not write | write |
|---|---|
| This is not a language verdict. | The dominant cost is the HTTP library. |
| a different request, not a slower client | a different request: the catalog adds a credential |
| The trade is not speed. | (delete it; the next sentence says what the trade is) |
| It is not the one with the bigger ratio. | Over the network the ratio falls to about 1x. |
| Nothing here is about X being broken. | (state the scope as a property, or delete) |
| One client does X, the other does not | Tip: pyiceberg checks the endpoint list first |

Literal factual negations are fine: "not run", "no TLS feature", "not an Azure VM".

**3. No sincerity or suspense filler.** "honest", "honestly", "actually", "the
truth", "frankly", "until it didn't", "turns out", "quietly", "silently", "the
interesting part", "here's the catch".

**4. Plain words, not the harness's vocabulary.** A reader outside the repo does
not know what "the control", a "probe", "expressible", "separable", "2xSEM", a
"floor", "loopback", "p50", "vended", "ambient ADC" or a "gate" is. Say "the
local Polaris catalog", "check", "supported", "bigger than the run-to-run noise",
"on the same machine", "median", "hands out a storage credential". Tool output in
code blocks stays verbatim.

**5. Pull the voice from the author's published work first.** dev.to:
`https://dev.to/api/articles?username=xbill`, then `body_markdown` per id. The
current house format is `####` headings, `---` between sections, one line per
paragraph (not hard-wrapped), `Step N —` sections, `🔎 Tip:` sections, a Compare
and Contrast table, `So, Which One?`, Summary bullets marked 🟢 ❌ ⚠️, one Scope
paragraph, the closing formula, then `#### References`.

```prose-lint
# SEVERITY | CATEGORY | regex | what to write instead
FAIL | narrative | \b(first|earlier|previous|original) (version|draft|attempt|pass)\b | report the result as it stands; no history of the work
FAIL | narrative | \b(earlier|first|previous|original|older) drafts?\b|\bdraft of this (article|work|paper)\b|\bthe draft (claimed|said|quoted|reported)\b | no history of the writing in the article
FAIL | narrative | \b(harness|our|my) (bugs?|mistakes?)\b | fix it silently; it goes in the commit message
FAIL | narrative | \b(runs?|results?) (were|was) (discarded|thrown away|redone)\b | state the method as a property
FAIL | narrative | \b(we|I) (found|caught|discovered|realized|realised|noticed|missed|fumbled)\b | state the finding, not who found it
FAIL | narrative | \bcost (a|us|me) (retry|day|rerun|re-run)\b | delete
FAIL | narrative | \bturn(s|ed) out\b | state the fact
FAIL | filler | \bhonest(ly)?\b|\bthe truth\b|\bfrankly\b|\bto be fair\b|\bcandid(ly)?\b | delete
FAIL | filler | \bactually\b|\bgenuinely\b|\bquietly\b|\bsilently\b|\bsurprising(ly)?\b | delete
FAIL | filler | \buntil it (did|didn'?t|did not)\b|\bhere'?s the (thing|catch)\b|\bthe catch\b|\bspoiler\b | state the fact
FAIL | filler | \bthe interesting (part|thing)\b|\bwhat matters (is|here)\b | state the fact
FAIL | contrast | (^|[.!?:]\s+)(this|that|it|they|these|those|the [\w-]+( [\w-]+)?) (is|are|was|were)( not|n'?t) | write the positive fact
FAIL | contrast | , not (a|an|the) [\w-]+( [\w-]+)?[.:;,] | write the positive fact; drop the foil
FAIL | contrast | \bnot about\b|\bis about\b[^.]*\bnot\b | write the positive fact
FAIL | contrast | (^|[.!?]\s+)(neither|nothing here|none of (this|that))\b | write the positive fact
FAIL | contrast | \bexactly (this|that)\b|\b(that|this) is the (finding|point|check|measurement|answer)\b|\bthe measurement to read\b | delete the pointer; state the result
FAIL | contrast | ;\s*this is (what|how|why)\b | two plain sentences
WARN | contrast | \brather than\b | usually a foil; check it is needed
FAIL | jargon | \bthe control\b|\bcontrol catalog\b | the local <name> catalog
FAIL | jargon | \bprobes?\b | check / test
FAIL | jargon | \bexpressible\b | supported
FAIL | jargon | \bseparable\b|\b2x ?SEM\b|\bSEM\b|\bbootstrap interval\b|\bdifferenced\b|\bcleared? the bound\b | bigger than the run-to-run noise
FAIL | jargon | \bdominant term\b|\bdecompos(e|ed|es|ition)\b | the biggest part / break down
FAIL | jargon | \bp(50|90|99)\b | median / 90th percentile
FAIL | jargon | \bloopback\b | on the same machine
FAIL | jargon | \bstatic bearer\b|\bambient (ADC|credentials)\b | the gcloud token / the machine's Google login
FAIL | jargon | \bvend(s|ed|ing)?\b | hands out a storage credential
WARN | jargon | \bharness\b|\bfixture\b|\binterleav(e|ed|ing)\b|\bfloor\b | a reader outside the repo may not know it
```

## Openers

> This article provides a step by step deployment guide for *X* to a *Y* hosted GPU
> enabled system. A suite of Python MCP tools is built to simplify management of the
> vLLM hosted deployment.

Then, immediately, the repository link on its own line.

## Recurring furniture

- Prerequisites under a heading phrased **"At this point you should have…"**
- Emoji status markers in tool output: ✅ 🟢 ❌
- **Medal emoji 🥇🥈🥉 rank options in comparison tables** — dev.to only
- Section headings in Title Case, some phrased as questions
  ("Where do I start?", "And Price/Performance?")

## Never put a self-measuring figure in a title

A title containing a number the article's own edits change is a title you have to
recompute after fixing a typo. "Getting 23 KB of Markdown Into AWS Builder Center"
was rewritten five times in one session — 19, 17, 20, 22, 23 — and the number told
a reader nothing, because it measured the writer's file rather than a result.

Numbers belong in titles when they are **findings**: "3.7x the Throughput", "the
Same Code". Not when they are properties of the document you are still editing.

The same applies to any count the work itself moves — how many scripts the
toolchain has, how many artifacts a run produces. State those where they are cheap
to regenerate, or derive them from a script, and keep them out of headlines,
covers and openers.

## Summary formula

> The goal of this article was to *X*. The key to the solution was *Y*.
> The *Z* results were:

followed by bullets, then **one** scope paragraph naming instrument and limits:
how many instances, which region, how many repeats, and any variable that differed
between compared runs. State it once and stop.

## Closings

- **dev.to:** *"The strategy for using MCP for … was validated with an incremental
  step by step approach."* The grammar is the author's. Keep it.
- **AWS Builder Center:** none of your own. The platform appends *"Any opinions in
  this article are those of the individual author and may not reflect the opinions
  of AWS."* under the tags, so a copy in the body shows twice. `make-builder.py`
  strips it.

## Medium publish settings

The author's defaults for Medium's publish dialog, stated 2026-09-10:

| Setting | Author's default | Medium's default |
|---|---|---|
| **Paywall this story** | **off** | on |
| **Notify your subscribers** | **on** | on |

The paywall stays off because the same article is free on dev.to. Set both
deliberately and read them back before clicking Publish — the dialog hydrates
late and a stray keystroke toggles them (`browser-publishing.md`). Notify is
the author's choice, but it still sends an email that cannot be recalled, so
publishing waits for an explicit go.

## Per-destination differences

| | dev.to | Builder Center | Medium | LinkedIn |
|---|---|---|---|---|
| Emoji | yes, medals in tables | **no** | inherits from dev.to source | renders, but not as status markers |
| Tables | native | native | images, via `make-medium.py` | **none** |
| Code | native | native, line-numbered | images if multi-line | **none** |
| Cover | 1376x578, `cover_image:` URL | 1200x675 upload, no text | first body image becomes cover | link preview card |
| Formatting | markdown | markdown | markdown | **none at all** |

## Where the numbers live

Benchmark artifacts are the citation, never prose. Reports validate against a
schema and live beside the run that produced them. A figure's `<hw-short>` is the
hardware **measured**, which is not necessarily the directory it sits in.
