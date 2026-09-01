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

REACH: A LABELLED ESTIMATE, NOT A COUNTER READING
-------------------------------------------------
"How many people read your content?" cannot be measured for an article that ran
in five places. Only dev.to exposes a view count over an API, it reads 0 for
hours after publishing, and the copies cannot be summed. So this defaults to the
author's standing estimate, DEFAULT_REACH, and **labels it an estimate in the
sheet.**

The labelling is the whole point, and it is what keeps this consistent with the
kit's rule against invented figures. That rule exists because a number presented
as a measurement invites a reader to trust it as one. An estimate the author
owns, marked as an estimate, is not that. A `page_views_count` copied silently
into this field would actually be the worse of the two -- it looks sourced and
understates the activity by four destinations.

Pass --reach N when a real, sourced number exists for a piece.

Date published is in the same dev.to response as the views, so it is read from
`published_at` rather than remembered. Override with --date.

    make-advocu.py <article>.md [--reach N] [--date YYYY-MM-DD] [--link URL]
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

# The author's standing estimate for a piece that ships to five destinations.
# See the header: this is an estimate by construction, and is written into the
# sheet as one.
DEFAULT_REACH = 3000

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


def devto_stats(url, key_path=pathlib.Path.home() / ".devto.key"):
    """Reach and publication date, from dev.to rather than from imagination.

    Returns (page_views_count, published_at_date) with either half possibly
    None. The date is in the same response as the views, so asking the author
    to remember it -- when the API knows it exactly -- is a made-up figure
    waiting to happen, in a form that reports to a program.
    """
    key = os.environ.get("DEV_TO_API_KEY") or (
        key_path.read_text().strip() if key_path.exists() else "")
    if not key:
        return None, None
    try:
        req = urllib.request.Request(
            "https://dev.to/api/articles/me?per_page=100",
            headers={"api-key": key, "User-Agent": "publishing-kit"})
        with urllib.request.urlopen(req, timeout=20) as r:
            for a in json.load(r):
                if a.get("url") and a["url"].rstrip("/") == url.rstrip("/"):
                    pub = (a.get("published_at") or "")[:10] or None
                    return a.get("page_views_count"), pub
    except Exception:
        return None, None
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--reach", type=int,
                    help=f"override the standing estimate of {DEFAULT_REACH}")
    ap.add_argument("--link", help="published URL; defaults to links.txt devto-gde")
    ap.add_argument("--date", help="YYYY-MM-DD; defaults to dev.to published_at")
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
    reach, date, reach_note = a.reach, a.date, ""
    if link and "temp-slug" not in link and date is None:
        v, pub = devto_stats(link)
        if pub:
            date = pub
            ok(f"date published {date} read from dev.to published_at")
        if v is not None:
            # Reported, never substituted: it counts one of five destinations.
            ok(f"dev.to page_views_count for this URL is {v} (one destination "
               f"of five, and 0 for hours after publishing -- not the reach)")
    if reach is None:
        reach = DEFAULT_REACH
        reach_note = " (standing estimate, not a counter reading)"
        ok(f"reach {reach}, the standing estimate. Pass --reach to override")
    else:
        ok(f"reach {reach}, given on the command line")
    if date is None:
        warn("no publication date. Pass --date YYYY-MM-DD")

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
{reach}{reach_note}

## Date published
{date or '(fill in the date it actually went public)'}

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
