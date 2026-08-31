#!/usr/bin/env python3
"""Paragraph unwrapping, in ONE place, because every destination needs it.

MEASURED 2026-08-31 -- and this reverses what SKILL.md used to imply. dev.to's
markdown renderer runs with hard breaks ON. A source hard-wrapped at ~95 columns
renders on dev.to with a `<br>` at every wrap, exactly like AWS Builder Center:

    47 of 62 paragraphs carried <br> in a published article, and the source had
    zero lines ending in the two spaces that mean an explicit markdown break.

So the ragged-break problem is not a Builder Center quirk. It is every
destination that takes markdown or a paste, and the only reason it was ever
described as a Builder Center problem is that Builder Center is where someone
happened to look.

Three callers, one implementation:

    serve-body.py     unwraps for the Builder Center paste
    publish-devto.py  unwraps before POSTing body_markdown
    check-article.py  reports hard-wrapped paragraphs before either runs

Everything whose line structure is load-bearing is left alone: fenced code,
tables, lists, headings, block quotes, horizontal rules, indented continuations.
"""

import re

FRONT = re.compile(r"\A(---\n.*?\n---\n)(.*)\Z", re.S)


def split_front_matter(text):
    """YAML front matter must never be unwrapped -- its lines are the record.

    Unwrapping it joins `title:`, `published:` and `tags:` into a single line and
    the destination sees no front matter at all.
    """
    m = FRONT.match(text)
    return (m.group(1), m.group(2)) if m else ("", text)


def unwrap(text: str) -> str:
    """Join hard-wrapped paragraph lines into one line each."""
    out, buf, fenced = [], [], False

    def flush():
        if buf:
            out.append(" ".join(x.strip() for x in buf))
            buf.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            fenced = not fenced
            out.append(line)
            continue
        if fenced:
            out.append(line)
            continue
        structural = (
            not stripped
            or stripped.startswith(("|", "#", ">", "- ", "* ", "+ ", "---", "==="))
            or (stripped[:2].rstrip(".").isdigit() and ". " in stripped[:4])
            or line[:1].isspace()          # indented: code or a continuation
        )
        if structural:
            flush()
            out.append(line)
        else:
            buf.append(line)
    flush()
    return "\n".join(out)


def unwrap_article(text: str) -> str:
    """Unwrap the body and leave the front matter exactly as it was."""
    fm, body = split_front_matter(text)
    return fm + unwrap(body)


def hard_wrapped(text: str):
    """Paragraphs spanning more than one source line, as (line number, excerpt).

    This is what renders with a ragged break. Reported before publishing rather
    than discovered on the published page.
    """
    _, body = split_front_matter(text)
    offset = len(text.splitlines()) - len(body.splitlines())
    found, start, count, fenced = [], None, 0, False
    lines = body.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        structural = (
            not stripped
            or stripped.startswith(("|", "#", ">", "- ", "* ", "+ ", "---", "==="))
            or (stripped[:2].rstrip(".").isdigit() and ". " in stripped[:4])
            or line[:1].isspace()
        )
        if structural:
            if count > 1:
                found.append((start + offset + 1, lines[start].strip()[:60]))
            start, count = None, 0
        else:
            if start is None:
                start = i
            count += 1
    if count > 1:
        found.append((start + offset + 1, lines[start].strip()[:60]))
    return found
