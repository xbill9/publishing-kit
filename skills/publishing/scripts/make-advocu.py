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

THE COVER IMAGE, AS WEBP
------------------------
Advocu now accepts WebP for an activity's image (author's report, 2026-09-15).
Every article already has a cover, so the activity gets one too:
`advocu-<stem>-cover.webp` beside the sheet. Which cover: `--cover FILE`, else a
`builder-cover*` beside the article (16:9, the shape a card shows best), else
the local file named by `cover_image:`. No cover found is a FAIL; `--no-cover`
opts out. The image is converted, never cropped, and scaled down only if it is
wider than MAX_COVER_WIDTH. Advocu's size and dimension limits are NOT measured
here -- read the upload widget's own hint when attaching it.

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
                   [--cover FILE | --no-cover]
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

# Covers are authored at 1200-1376px wide. Anything wider is scaled down to keep
# the upload small; nothing is ever cropped.
MAX_COVER_WIDTH = 1600

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


def devto_stats(url, key_path=None):
    """Reach and publication date, from dev.to rather than from imagination.

    Returns (page_views_count, published_at_date) with either half possibly
    None. The date is in the same response as the views, so asking the author
    to remember it -- when the API knows it exactly -- is a made-up figure
    waiting to happen, in a form that reports to a program.
    """
    key_path = key_path or pathlib.Path.home() / ".devto.key"
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


def find_cover(article, fm, explicit):
    """The activity's image: explicit, else the 16:9 Builder cover, else cover_image."""
    if explicit:
        p = pathlib.Path(explicit).expanduser().resolve()
        return p if p.exists() else None
    for pattern in ("builder-cover*.jpg", "builder-cover*.png", "builder-cover*.webp"):
        hits = sorted(article.parent.glob(pattern))
        if hits:
            return hits[0]
    url = field(fm, "cover_image")
    if url:
        local = article.parent / url.rsplit("/", 1)[-1]
        if local.exists():
            return local
    return None


def write_webp(src, out):
    """Convert to WebP; scale down only past MAX_COVER_WIDTH, never crop."""
    from PIL import Image  # make-cover.py already needs Pillow; only this path does here

    im = Image.open(src).convert("RGB")
    w, h = im.size
    if w > MAX_COVER_WIDTH:
        im = im.resize((MAX_COVER_WIDTH, round(h * MAX_COVER_WIDTH / w)), Image.LANCZOS)
    im.save(out, "WEBP", quality=88, method=6)
    return (w, h), im.size, out.stat().st_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--reach", type=int,
                    help=f"override the standing estimate of {DEFAULT_REACH}")
    ap.add_argument("--link", help="published URL; defaults to links.txt devto-gde")
    ap.add_argument("--date", help="YYYY-MM-DD; defaults to dev.to published_at")
    ap.add_argument("--type", default="Articles", choices=TYPES)
    ap.add_argument("--cover", help="image for the activity; default builder-cover*, "
                                    "then the article's cover_image")
    ap.add_argument("--no-cover", action="store_true",
                    help="file the activity without an image")
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
    out.parent.mkdir(parents=True, exist_ok=True)
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

    # 4  THE COVER -----------------------------------------------------------
    cover_out = out.with_name(f"{out.stem}-cover.webp")
    cover_line = "(none: --no-cover)"
    if a.no_cover:
        warn("--no-cover: the activity is filed without an image")
    else:
        cover = find_cover(src, fm, a.cover)
        if cover is None:
            fail("no cover image found (--cover FILE, builder-cover* or a local file "
                 "matching cover_image: beside the article); pass --no-cover to skip")
        else:
            try:
                (sw, sh), (cw, ch), size = write_webp(cover, cover_out)
                ok(f"cover {cover.name} {sw}x{sh} -> {cover_out.name} {cw}x{ch} "
                   f"WebP, {size // 1024} KB (not cropped)")
                cover_line = f"{cover_out.name} ({cw}x{ch} WebP, {size // 1024} KB, from {cover.name})"
            except Exception as e:  # a broken image must not look like success
                fail(f"could not convert {cover.name} to WebP: {e}")

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

## Cover image
{cover_line}

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
