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

GOOGLE CHAT MARKUP, AND WHAT IS NOT MEASURED HERE
-------------------------------------------------
Chat's own markup is *bold*, _italic_, ~strike~ and `code` -- close enough to
Slack's mrkdwn that markdown `**bold**` and `[label](url)` are wrong in both. So
this strips markdown rather than translating it, and puts a bare URL on its own
line for Chat to unfurl, which is what the Slack post does.

Everything past that is UNVERIFIED and deliberately not claimed: this kit's rule
is that a destination's behaviour is measured or it is not written down. Nobody
has yet checked, in the GDE Americas space, whether a hashtag does anything,
what the composer is made of, or whether Enter sends. Until someone does, treat
it like Slack -- assume Enter sends, and paste rather than type.

NO HASHTAGS BY DEFAULT
----------------------
The Slack post ends in hashtags because the author's posts in that channel do.
Whether they are idiomatic in the GDE space is not established, so --hashtags
exists and is empty unless you pass it.

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
    return ("{context}\n\nDev.to is here:\n{devto}\n\nMedium is here:\n{medium}\n\n"
            "Builder Center Article is here:\n{builder}\n\n"
            "Linked In is here:\n{linkedin}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--context", help="file with the opening lines; defaults to "
                                      "the article's own first paragraphs")
    ap.add_argument("--hashtags", default="",
                    help="empty by default: not established as idiomatic here")
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
    ctx = (pathlib.Path(a.context).read_text().strip() if a.context
           else "\n".join(context_lines(text)))
    post = load_template().format(
        context=ctx, devto=resolved.get("devto-gde", ""),
        medium=resolved.get("medium", ""), builder=resolved.get("builder", ""),
        linkedin=resolved.get("linkedin", "")).strip()
    if a.hashtags:
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
