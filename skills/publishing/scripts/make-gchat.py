#!/usr/bin/env python3
"""Prepare the GDE Americas (Google Chat) post for a published article. OPTIONAL.

The same job as make-slack.py, for the other community. Optional and after the
fact: nothing else in the kit calls it.

WHY THIS IS NOT make-slack.py WITH A DIFFERENT TEMPLATE
-------------------------------------------------------
It is the same shape -- a few lines of plain context, then one labelled link per
destination -- because that is the author's own format and the point is that a
reader in either community sees something familiar. What differs is which copy
of the article the community gets:

    #boost-ai-engineering (AWS)   ->  dev.to/aws-builders
    GDE Americas (Google)         ->  dev.to/gde

Sending a Google community the AWS org's copy is the same mistake as sending an
AWS community the Google one, in the other direction, and this script fails on
it exactly the way make-slack.py does. The link order flips for the same reason:
lead with the copy that belongs to the room you are posting in.

THE SHAPE IS THIS ROOM'S, NOT SLACK'S
-------------------------------------
MEASURED 2026-09-01 by reading the author's own last post in GDEs - Americas
rather than porting the Slack template across. The room reads differently:

    Slack (#boost-ai-engineering)      GDE Americas (Google Chat)
    ------------------------------     --------------------------------
    straight into the context          opens with why you are posting
    label line, then URL alone         "... is here: <url>", inline
    four links, then hashtags          links inline, no hashtags anywhere

The author's post there opens "Just posting in case this helps someone out
with ..." and closes "My renewal post on LinkedIn is here: <url>" on one line.
So this emits a lede, the context, then one inline labelled link per line. The
lede is a template field: rewrite it per article, do not ship the default
because it was there.

NO HASHTAGS, AND THIS ONE IS NOT A STYLE OPINION
------------------------------------------------
MEASURED, with a control: typing `@All` opens Chat's People picker, and typing
`#ClaudeCode` opens **the same picker** -- People and Files, with "all / Notify
all" as the first entry. `#` is not inert in Google Chat the way it is in a
document; it is a second mention trigger. Enter with that list open inserts
whatever is highlighted, and what is highlighted first is a notify-everyone.

The control matters: `@` alone opened nothing, and so did `#` alone, which would
have read as "hashtags are safe here". Both pickers need a following letter.
Test the thing that fires before believing the thing that does not.

So --hashtags exists, is empty, and warns when you pass it.

GOOGLE CHAT MARKUP
------------------
Chat's markup is *bold*, _italic_, ~strike~ and `code` -- close enough to
Slack's mrkdwn that markdown `**bold**` and `[label](url)` are wrong in both, so
this strips markdown rather than translating it.

Still not measured: whether Enter sends. Assume it does, and paste rather than
type. `execCommand("insertText")` puts the whole message in at once and,
usefully, does NOT trigger the pickers that real keystrokes do.

THIS SCRIPT DOES NOT POST
-------------------------
It writes a file. Sending into a shared community space is a person's decision.

    make-gchat.py <article>.md [--context FILE] [--hashtags "#A #B"]
"""

import argparse
import pathlib
import re
import sys
import urllib.error
import urllib.request

# Empty on purpose. A manufactured "just posting in case this helps..." line was
# the default here for exactly one post, and the author cut it before sending:
# that opening belongs to a help-someone-out post, not to an article
# announcement, which earns its place with the first line of the article itself.
# Pass --lede when a particular piece actually needs a why-I-am-posting line.
DEFAULT_LEDE = ""

FAILS, WARNS = [], []
# dev.to first: this is the Google community and dev.to/gde is its copy.
ORDER = [("devto-gde", "Dev.to (gde)"), ("medium", "Medium"),
         ("builder", "Builder Center"), ("linkedin", "LinkedIn")]


def fail(m):
    FAILS.append(m); print(f"  FAIL  {m}")


def warn(m):
    WARNS.append(m); print(f"  WARN  {m}")


def ok(m):
    print(f"  ok    {m}")


def strip_markdown(s):
    """Chat renders none of it; leftovers ship as punctuation."""
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"(?<!\w)[*_]([^*_]+)[*_](?!\w)", r"\1", s)
    return re.sub(r"\s+", " ", s.replace("`", "")).strip()


def links_file(d):
    out = {}
    f = d / "links.txt"
    if f.exists():
        for ln in f.read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, _, v = ln.partition("=")
                out[k.strip()] = v.strip()
    return out


def context_lines(text, n=3):
    """The article's own opening paragraphs, markdown stripped."""
    _, _, body = text.partition("\n---\n")
    body = re.sub(r"^>.*$", "", body, flags=re.M)          # drop the TL;DR quote
    paras, buf = [], []
    for line in body.splitlines():
        if line.strip().startswith(("#", "```", "|", "-")):
            continue
        if line.strip():
            buf.append(line.strip())
        elif buf:
            paras.append(" ".join(buf)); buf = []
        if len(paras) >= n:
            break
    return [strip_markdown(p) for p in paras[:n]]


def load_template():
    p = pathlib.Path(__file__).resolve().parent.parent / "templates" / "gchat-post.txt"
    if p.exists():
        return p.read_text()
    return ("{lede}\n\n{context}\n\nDev.to is here: {devto}\n\n"
            "Medium is here: {medium}\n\n"
            "Builder Center article is here: {builder}\n\n"
            "My LinkedIn post is here: {linkedin}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--context", help="file with the opening lines; defaults to "
                                      "the article's own first paragraphs")
    ap.add_argument("--lede", help="the opening 'why I am posting this' line")
    ap.add_argument("--hashtags", default="",
                    help="empty, and warned about: # opens Chat's mention picker")
    ap.add_argument("--out")
    a = ap.parse_args()

    src = pathlib.Path(a.article).resolve()
    d = src.parent
    text = src.read_text()
    links = links_file(d)
    out = pathlib.Path(a.out) if a.out else d / f"gchat-{src.stem}.txt"

    print(f"\n{src.name} -> {out.name}")

    # 1  EVERY LINK, AND THE RIGHT DEV.TO ONE --------------------------------
    resolved = {}
    for key, label in ORDER:
        v = links.get(key, "")
        if not v or v.upper() == "PENDING":
            fail(f"{label} link is PENDING")
        elif "temp-slug" in v:
            fail(f"{label} link is an unpublished draft URL: {v}")
        elif not v.startswith("https://"):
            fail(f"{label} link is not https: {v}")
        else:
            try:
                req = urllib.request.Request(v, headers={"User-Agent": "publishing-kit"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    ok(f"{label}: HTTP {r.status}")
            except urllib.error.HTTPError as e:
                fail(f"{label}: HTTP {e.code}")
            except Exception as e:
                warn(f"{label}: could not reach it ({e})")
        resolved[key] = v or "PENDING"

    # The mirror of make-slack.py's check, and it fires on the opposite error.
    aws = links.get("devto-aws", "")
    gde = resolved.get("devto-gde", "")
    if aws and gde.startswith("https://") and gde == aws:
        fail("the dev.to link is the aws-builders copy. This is the Google "
             "community's space; send them the gde one")
    elif gde.startswith("https://") and "/gde/" not in gde:
        warn(f"the dev.to link is not under /gde/: {gde}")
    else:
        ok("the dev.to link is the GDE org's copy")

    # 2  BUILD ---------------------------------------------------------------
    # Blank lines between paragraphs, because that is how the room reads. The
    # Slack post runs them together; this one does not.
    ctx = (pathlib.Path(a.context).read_text().strip() if a.context
           else "\n\n".join(context_lines(text)))
    lede = a.lede if a.lede is not None else DEFAULT_LEDE
    post = load_template().format(
        lede=lede, context=ctx, devto=resolved.get("devto-gde", ""),
        medium=resolved.get("medium", ""), builder=resolved.get("builder", ""),
        linkedin=resolved.get("linkedin", "")).strip()
    post = re.sub(r"\A\n+", "", post)          # no gap where an empty lede was
    if a.hashtags:
        warn("--hashtags: in Google Chat a # opens the People/Files picker, "
             "with notify-all first in the list. Measured 2026-09-01. Drop them "
             "or clear the picker with Escape before Enter")
        post += "\n\n" + a.hashtags
    post += "\n"

    # 3  CHAT RENDERS NO MARKDOWN --------------------------------------------
    leftovers = [m for m in ("**", "](", "`", "##") if m in post]
    if leftovers:
        fail(f"markdown left in the post, which Chat renders literally: {leftovers}")
    else:
        ok("no markdown left; Chat renders none of it")

    out.write_text(post)
    print(f"\n{len(FAILS)} fail, {len(WARNS)} warn")
    print("\nThis script does not post. Paste it into the space yourself and "
          "read it back before sending. Assume Enter sends until measured.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
