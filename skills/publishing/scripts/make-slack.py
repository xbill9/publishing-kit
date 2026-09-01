#!/usr/bin/env python3
"""Prepare the AWS Community Builders Slack post for a published article. OPTIONAL.

Announces one article in a community channel with a link to each destination.
Optional and after the fact: nothing else in the kit calls it.

THE FORMAT IS THE AUTHOR'S OWN, READ OUT OF THE CHANNEL
------------------------------------------------------
Taken from the author's previous post in #boost-ai-engineering on 2026-09-01
rather than invented:

    <two or three lines of plain context: the problem, the alternative, what
     you actually did>
    Builder Center Article is here:
    <link>
    Medium is here:
    <link>
    Dev.to is here:
    <link>
    Linked In is here:
    <link>
    #Tag #Tag #Tag

Note the order -- Builder Center, Medium, Dev.to, LinkedIn -- and that the
dev.to link is the **aws-builders** one, not the GDE one. It is an AWS community
channel; sending them the Google org's copy of the same article is the kind of
detail nobody mentions and everybody notices.

The shape lives in `templates/slack-post.txt`. Swap it and the post changes.

SLACK IS NOT MARKDOWN
---------------------
Slack's composer is WYSIWYG and its own markup is mrkdwn: `*bold*` with single
asterisks, `_italic_`, `<url|label>` for a labelled link. Markdown `**bold**`
arrives as literal asterisks and `[label](url)` as literal brackets. This script
strips markdown rather than translating it, because a bare URL on its own line is
what the author's existing posts do and Slack unfurls it.

THIS SCRIPT DOES NOT POST
-------------------------
It writes a file. Sending into a shared community channel is a person's decision,
and there is no undo that the other 656 members will not have already seen.

    make-slack.py <article>.md [--context FILE] [--hashtags "#A #B"]
"""

import argparse
import pathlib
import re
import sys
import urllib.error
import urllib.request

FAILS, WARNS = [], []
ORDER = [("builder", "Builder Center"), ("medium", "Medium"),
         ("devto-aws", "Dev.to (aws-builders)"), ("linkedin", "LinkedIn")]


def fail(m):
    FAILS.append(m); print(f"  FAIL  {m}")


def warn(m):
    WARNS.append(m); print(f"  WARN  {m}")


def ok(m):
    print(f"  ok    {m}")


def front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else ""


def field(fm, key):
    m = re.search(rf'^{key}:\s*"?(.*?)"?\s*$', fm, re.M)
    return m.group(1) if m else ""


def strip_markdown(s):
    """Slack renders none of it; leftovers ship as punctuation."""
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
    p = pathlib.Path(__file__).resolve().parent.parent / "templates" / "slack-post.txt"
    if p.exists():
        return p.read_text()
    return ("{context}\n\nBuilder Center Article is here:\n{builder}\n\n"
            "Medium is here:\n{medium}\n\nDev.to is here:\n{devto}\n\n"
            "Linked In is here:\n{linkedin}\n\n{hashtags}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--context", help="file with the opening lines; defaults to "
                                      "the article's own first paragraphs")
    ap.add_argument("--hashtags", default="")
    ap.add_argument("--out")
    a = ap.parse_args()

    src = pathlib.Path(a.article).resolve()
    d = src.parent
    text = src.read_text()
    links = links_file(d)
    out = pathlib.Path(a.out) if a.out else d / f"slack-{src.stem}.txt"

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
                # Medium answers any non-browser client with 403 -- documented in
                # references/browser-publishing.md, which says to verify a published
                # Medium article with get_page_text in the browser and not from the
                # shell. Treating that as a broken link fails the run on a link that
                # is fine, which is worse than not checking it.
                if e.code == 403 and "medium.com" in v:
                    warn(f"{label}: HTTP 403, which is what Medium answers every "
                         f"non-browser client. Verify it in the browser, not here.")
                else:
                    fail(f"{label}: HTTP {e.code}")
            except Exception as e:
                warn(f"{label}: could not reach it ({e})")
        resolved[key] = v or "PENDING"

    gde = links.get("devto-gde", "")
    aws = resolved.get("devto-aws", "")
    # only meaningful once both are real: two PENDINGs compare equal and the
    # check fired on that, which is a false alarm and those get switched off
    if gde and aws.startswith("https://") and aws == gde:
        fail("the dev.to link is the GDE org's copy. This is an AWS community "
             "channel; send them the aws-builders one")

    # 2  BUILD ---------------------------------------------------------------
    ctx = (pathlib.Path(a.context).read_text().strip() if a.context
           else "\n".join(context_lines(text)))
    post = load_template().format(
        context=ctx, builder=resolved.get("builder", ""),
        medium=resolved.get("medium", ""), devto=resolved.get("devto-aws", ""),
        linkedin=resolved.get("linkedin", ""), hashtags=a.hashtags).strip() + "\n"

    # 3  SLACK RENDERS NO MARKDOWN -------------------------------------------
    leftovers = [m for m in ("**", "](", "`", "##") if m in post]
    if leftovers:
        fail(f"markdown left in the post, which Slack renders literally: {leftovers}")
    else:
        ok("no markdown left; Slack renders none of it")

    out.write_text(post)
    print(f"\n{len(FAILS)} fail, {len(WARNS)} warn")
    print("\nThis script does not post. Paste it into the channel yourself and "
          "read it back before sending.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
