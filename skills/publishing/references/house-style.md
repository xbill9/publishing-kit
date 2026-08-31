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

## Summary formula

> The goal of this article was to *X*. The key to the solution was *Y*.
> The *Z* results were:

followed by bullets, then **one** scope paragraph naming instrument and limits:
how many instances, which region, how many repeats, and any variable that differed
between compared runs. State it once and stop.

## Closings

- **dev.to:** *"The strategy for using MCP for … was validated with an incremental
  step by step approach."* The grammar is the author's. Keep it.
- **AWS Builder Center:** *"Any opinions in this article are those of the individual
  author and may not reflect the opinions of AWS."* Required.

## Per-destination differences

| | dev.to | Builder Center | Medium |
|---|---|---|---|
| Emoji | yes, medals in tables | **no** | inherits from dev.to source |
| Tables | native | native | images, via `make-medium.py` |
| Code | native | native, line-numbered | images if multi-line |
| Cover | 1376x768, `cover_image:` URL | 1200x675 upload, no text | first body image becomes cover |

## Where the numbers live

Benchmark artifacts are the citation, never prose. Reports validate against a
schema and live beside the run that produced them. A figure's `<hw-short>` is the
hardware **measured**, which is not necessarily the directory it sits in.
