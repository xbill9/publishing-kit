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
tables, lists, headings, horizontal rules, indented continuations, reference
definitions, nested quotes and two-space hard breaks.

BLOCK QUOTES ARE NOT IN THAT LIST, and used to be. Only the `>` prefix carries
meaning in a quote; the line breaks inside it are wrapping like any other
paragraph. Left alone, a hard-wrapped TL;DR posts as five separate lines and
dev.to renders a break at each one -- and `hard_wrapped()` shared the blind spot,
so the pre-flight reported nothing to fix.
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


FENCE_OPEN = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
HARD_BREAK = re.compile(r"\S {2,}$")
ORDERED = re.compile(r"^\d{1,9}[.)](\s|$)")
REFERENCE_DEF = re.compile(r"^\[[^\]]+\]:")


def fence_kinds(lines):
    """Classify each line as "", "open", "body" or "close".

    THE ONE FENCE PARSER. MEASURED 2026-10-31: nine files had their own
    fence logic and eight tested only for backticks, so a `~~~` block was prose
    to them, and a four-backtick fence holding a three-backtick example closed at
    its first inner line. CommonMark's rule: a close uses the opener's character, is at least as
    long, and carries nothing else. A fence never closed runs to the end. Any
    indent opens one, because a fence inside a list item is indented.
    """
    kinds, marker = [], None
    for line in lines:
        s = line.strip()
        if marker is None:
            m = FENCE_OPEN.match(line)
            # a backtick info string cannot hold a backtick: ```x``` is inline code
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                marker = m.group(1)
                kinds.append("open")
            else:
                kinds.append("")
        elif s and set(s) == {marker[0]} and len(s) >= len(marker):
            marker = None
            kinds.append("close")
        else:
            kinds.append("body")
    return kinds


def strip_fenced(text):
    """TEXT without its fenced blocks, delimiters included."""
    lines = text.splitlines()
    return "\n".join(ln for ln, k in zip(lines, fence_kinds(lines)) if not k)


def _quote_body(line):
    """The text of a `>` line, or None if it is not a plain quoted paragraph line."""
    st = line.strip()
    if not st.startswith(">"):
        return None
    inner = st[1:].strip()
    if not inner:
        return ""                                   # blank quote line: a break
    if (inner.startswith(("|", "#", "- ", "* ", "+ ", "```", "~~~", "---", ">"))
            or ORDERED.match(inner) or REFERENCE_DEF.match(inner)):
        return None                                 # structure inside the quote
    return inner


def _structural(line):
    """A line whose own break is load-bearing, so it never joins a paragraph."""
    s = line.strip()
    return (not s
            or s.startswith(("|", "#", ">", "- ", "* ", "+ ", "---", "==="))
            or bool(ORDERED.match(s))
            or bool(REFERENCE_DEF.match(s))
            or line[:1].isspace())                  # indented: code or a continuation


def unwrap(text: str) -> str:
    """Join hard-wrapped paragraph lines into one line each, quotes included.

    MEASURED 2026-10-31: two spaces at a line end are the author's explicit
    break, so joining across one deletes something they wrote on purpose. The
    paragraph is flushed there and the two spaces stay.
    """
    out, buf, quote = [], [], []

    def flush(tail=""):
        if buf:
            out.append(" ".join(x.strip() for x in buf) + tail)
            buf.clear()

    def flush_quote(tail=""):
        if quote:
            out.append("> " + " ".join(quote) + tail)
            quote.clear()

    lines = text.splitlines()
    for line, kind in zip(lines, fence_kinds(lines)):
        if kind == "open":
            flush(); flush_quote()
        if kind:
            out.append(line)
            continue

        q = _quote_body(line)
        if q is not None:
            flush()
            if q == "":                             # blank line inside the quote
                flush_quote()
                out.append(">")
            else:
                quote.append(q)
                if HARD_BREAK.search(line):
                    flush_quote("  ")
            continue
        flush_quote()

        if _structural(line):
            flush()
            out.append(line)
        else:
            buf.append(line)
            if HARD_BREAK.search(line):
                flush("  ")
    flush(); flush_quote()
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
    found, start, count = [], None, 0
    lines = body.splitlines()

    def close():
        nonlocal start, count
        if count > 1:
            found.append((start + offset + 1, lines[start].strip()[:60]))
        start, count = None, 0

    for i, (line, kind) in enumerate(zip(lines, fence_kinds(lines))):
        if kind:
            close()
            continue
        q = _quote_body(line)
        if q or not (q is not None or _structural(line)):
            if start is None:
                start = i
            count += 1
            if HARD_BREAK.search(line):             # an explicit break ends the run
                close()
        else:
            close()
    close()
    return found


def skipped(value):
    """A links.txt value of SKIP: the article is deliberately not published there.

    PENDING means "not yet" and fails every announcement, which is right until the
    author decides a destination is out -- Medium refusing an account, say. Then
    PENDING can never clear and the only escape was deleting the line, which also
    deletes the check that it is missing. SKIP keeps the line and says why it has
    no URL; every consumer leaves that destination out of what it writes.
    """
    return (value or "").strip().upper() == "SKIP"


def links_path(article):
    """The links file for ARTICLE: ``<stem>.links.txt`` beside it, else ``links.txt``.

    A directory can hold two articles -- part 1 and part 2 of a series -- and a
    single ``links.txt`` would hand one article's URLs to the other's
    announcement. The per-article name wins when it exists; a directory with one
    article keeps working unchanged.
    """
    import pathlib
    src = pathlib.Path(article)
    own = src.with_name(f"{src.stem}.links.txt")
    return own if own.exists() else src.with_name("links.txt")
