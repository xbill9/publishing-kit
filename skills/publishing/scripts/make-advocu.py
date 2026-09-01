#!/usr/bin/env python3
"""Prepare a GDE Advocu activity from a published article. OPTIONAL, GDE only.

Advocu (app.advocu.com) is where a Google Developer Expert records activities.
This is not part of publishing -- the article is already out by the time it is
relevant -- so nothing else in the kit depends on it and nothing calls it
automatically.

MEASURED 2026-09-01 in the Google Developer Experts workspace.

TWO ROUTES, AND THE AI ONE TAKES A LINK, NOT YOUR TEXT
------------------------------------------------------
Add new activity -> New activity -> Content creation gives:

    Generate your activity with AI    "Just paste the link to the activity you
                                       want to add" -- a URL field. It does not
                                       take the LinkedIn post's text.
    or continue with -> Regular form   the seven fields below.

So the AI route needs the article to be PUBLISHED and reachable. Until then the
regular form is the only one that can be filled, and it needs the URL too:
`Link to Content` is required.

THE FORM, STEP 1 "Content details"
----------------------------------
    Content type *      Articles | Books | Code contribution | Demos |
                        Newsletters | Podcasts | Videos
    What was the title? *
    What was it about? *    rich text: bold, italic, underline, strike, link,
                            ordered and unordered lists
    Tags                    picker
    How many people read your content? *   a number
    Date published *
    Link to Content *       https://

Step 2 is "Additional information". There is a **Save as draft**, so an activity
can be parked exactly like every other destination in this kit.

REACH IS A MEASUREMENT AND THIS SCRIPT WILL NOT INVENT ONE
----------------------------------------------------------
"How many people read your content?" is a number that goes into someone's
program statistics. Pass it with --reach from a real source -- dev.to's own
`page_views_count`, a Medium stats page -- or leave it out and fill it in by
hand. Guessing here is the same failure as any untraced figure in the article,
with the difference that this one is reported to a program.

    make-advocu.py <article>.md [--reach N] [--link URL] [--type Articles]
"""

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

TYPES = ["Articles", "Books", "Code contribution", "Demos",
         "Newsletters", "Podcasts", "Videos"]

FAILS, WARNS = [], []


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


def links_file(d):
    f = d / "links.txt"
    out = {}
    if f.exists():
        for ln in f.read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, _, v = ln.partition("=")
                out[k.strip()] = v.strip()
    return out


def devto_views(url, key_path=pathlib.Path.home() / ".devto.key"):
    """Reach, from dev.to's own counter rather than from imagination."""
    key = os.environ.get("DEV_TO_API_KEY") or (
        key_path.read_text().strip() if key_path.exists() else "")
    if not key:
        return None
    try:
        req = urllib.request.Request(
            "https://dev.to/api/articles/me?per_page=100",
            headers={"api-key": key, "User-Agent": "publishing-kit"})
        with urllib.request.urlopen(req, timeout=20) as r:
            for a in json.load(r):
                if a.get("url") and a["url"].rstrip("/") == url.rstrip("/"):
                    return a.get("page_views_count")
    except Exception:
        return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--reach", type=int,
                    help="how many people read it, from a real counter")
    ap.add_argument("--link", help="published URL; defaults to links.txt devto-gde")
    ap.add_argument("--type", default="Articles", choices=TYPES)
    ap.add_argument("--out")
    a = ap.parse_args()

    src = pathlib.Path(a.article).resolve()
    d = src.parent
    text = src.read_text()
    fm = front_matter(text)
    title = field(fm, "title")
    desc = field(fm, "description")
    tags = [t.strip() for t in field(fm, "tags").split(",") if t.strip()]

    links = links_file(d)
    link = a.link or links.get("devto-gde") or ""

    out = pathlib.Path(a.out) if a.out else d / f"advocu-{src.stem}.md"
    print(f"\n{src.name} -> {out.name}")

    # 1  THE LINK ------------------------------------------------------------
    if not link or link.upper() == "PENDING":
        fail("no published URL. Advocu requires Link to Content, and the AI "
             "route takes a link rather than your text -- so the article has to "
             "be published before an activity can be filed at all")
    elif "temp-slug" in link:
        fail(f"the link is an unpublished dev.to draft whose slug changes on "
             f"publish: {link}")
    else:
        try:
            req = urllib.request.Request(link, headers={"User-Agent": "publishing-kit"})
            with urllib.request.urlopen(req, timeout=20) as r:
                ok(f"link resolves: HTTP {r.status}")
        except urllib.error.HTTPError as e:
            fail(f"link returns HTTP {e.code}: {link}")
        except Exception as e:
            warn(f"could not reach the link ({e}): {link}")

    # 2  REACH ---------------------------------------------------------------
    reach = a.reach
    if reach is None and link and "temp-slug" not in link:
        reach = devto_views(link)
        if reach is not None:
            ok(f"reach {reach} read from dev.to page_views_count")
    if reach is None:
        warn("no reach figure. Pass --reach from a real counter, or fill the "
             "field by hand -- this script will not invent a number that goes "
             "into your program statistics")

    # 3  FIELDS --------------------------------------------------------------
    for label, value in (("title", title), ("description", desc)):
        (ok if value else fail)(f"{label} present" if value else f"{label} missing from front matter")

    body = f"""# Advocu activity — paste into app.advocu.com

Add new activity -> New activity -> Content creation -> Regular form.
Once the article is public you can instead paste the Link to Content into
"Generate your activity with AI" and check what it produces against this.

## Content type
{a.type}

## What was the title?
{title}

## What was it about?
{desc}

## Tags
{', '.join(tags) if tags else '(none in front matter)'}

## How many people read your content?
{reach if reach is not None else '(fill in from a real counter)'}

## Date published
(the date it actually went public)

## Link to Content
{link or '(PENDING — the article is not published)'}

---
Save as draft rather than submitting, and read it back before you do.
"""
    out.write_text(body)
    print(f"\n{len(FAILS)} fail, {len(WARNS)} warn")
    if FAILS:
        print("\nThe sheet was written so you can read it. It is not fileable yet.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
