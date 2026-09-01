#!/usr/bin/env python3
"""Create and update dev.to articles over the REST API. No browser, ever.

dev.to is the only destination of the four with a complete publishing API, and
the front matter IS the payload -- title, tags and cover_image all ride inside
`body_markdown`, so nothing is retyped and no cover is uploaded by hand.

    publish-devto.py --list
    publish-devto.py --create <article>.md [--org gde]
    publish-devto.py --update <id> <article>.md
    publish-devto.py --org <id> <org-slug>

THE PRE-FLIGHT GATES THE PUBLISH. --create and --update run check-article.py
first and refuse on any FAIL, because every check in it describes something that
is invisible locally and permanent once published. --force is deliberate.

The key is read from $DEV_TO_API_KEY or ~/.devto.key and is never accepted on the
command line, where it would land in shell history and process listings.

Two API behaviours worth knowing, both recorded in SKILL.md:

  * `GET /api/articles/<id>` returns 404 for some published articles even with a
    valid key, while the same article lists normally in /api/articles/me. Read
    state from the listing, which is what --list does.
  * **/api/articles/me EXCLUDES drafts.** MEASURED 2026-08-31: an article created
    with `published: false` does not appear there at all, at any page size. Drafts
    live at /api/articles/me/unpublished, so a --list built on the first endpoint
    alone is blind to exactly what this script produces. --list reads both.
  * There is no delete endpoint. An article created here can be edited forever
    and never removed.
  * **A slug is fixed at creation.** Renaming the article later does not move it,
    so a draft created under a working title keeps that title's URL for good.
    Create the draft with the title you mean to publish under, or replace it.
  * MEASURED 2026-08-31: creating two articles with the SAME title inside five
    minutes returns 422 `Title has already been used in the last five minutes`.
    Posting one piece to two organizations therefore needs a pause between the
    two creates.
  * MEASURED 2026-08-31: a request without a `User-Agent` header is answered
    403 `Forbidden Bots`. This script always sends one; hand-rolled curl or
    urllib calls need it too.

`organization_id` is a separate call after the article exists -- front matter
cannot express it. There is no "list my organizations" endpoint either, so the
slug is resolved through /api/organizations/<slug>.
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

from bodytext import hard_wrapped, unwrap_article

API = "https://dev.to/api"


def key():
    k = os.environ.get("DEV_TO_API_KEY")
    if not k:
        f = pathlib.Path.home() / ".devto.key"
        if f.exists():
            k = f.read_text().strip()
    if not k:
        sys.exit("no key: set $DEV_TO_API_KEY or write ~/.devto.key (chmod 600)")
    return k


def call(method, path, payload=None):
    req = urllib.request.Request(
        f"{API}{path}", method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"api-key": key(), "Content-Type": "application/json",
                 "User-Agent": "publishing-kit"})
    try:
        with urllib.request.urlopen(req) as r:
            body = r.read().decode()
            return r.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:400]}


def preflight(article, force):
    """Refuse to publish anything the pre-flight fails. It exits non-zero."""
    checker = pathlib.Path(__file__).with_name("check-article.py")
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          cwd=article.parent, capture_output=True, text=True).stdout.strip()
    r = subprocess.run([sys.executable, str(checker), str(article),
                        "--repo-root", root or "."], capture_output=True, text=True)
    print(r.stdout.rstrip())
    if r.returncode and not force:
        sys.exit("\nrefusing to publish: the pre-flight failed. --force overrides.")
    if r.returncode:
        print("\n--force given; publishing over a failed pre-flight")


def show(a):
    org = (a.get("organization") or {}).get("username")
    state = "published" if a.get("published") else "draft"
    print(f"  {a['id']:>8}  {state:<9}  org={org or '-':<14}  {a.get('title','')[:52]}")
    if a.get("url"):
        print(f"            {a['url']}")


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--create", metavar="ARTICLE")
    g.add_argument("--update", nargs=2, metavar=("ID", "ARTICLE"))
    g.add_argument("--org", nargs=2, metavar=("ID", "SLUG"))
    p.add_argument("--org-slug", dest="org_on_create",
                   help="with --create: route to this organization afterwards")
    p.add_argument("--no-unwrap", action="store_true",
                   help="post the source's hard wraps as-is; dev.to renders each "
                        "one as a line break")
    p.add_argument("--force", action="store_true",
                   help="publish even though the pre-flight failed")
    a = p.parse_args()

    if a.list:
        st, pub = call("GET", "/articles/me?per_page=30")
        if st != 200:
            sys.exit(f"list failed: {st} {pub}")
        st2, dra = call("GET", "/articles/me/unpublished?per_page=30")
        dra = dra if st2 == 200 else []
        print(f"{len(dra)} draft(s)")
        for x in dra:
            show(x)
        print(f"\n{len(pub)} published")
        for x in pub:
            show(x)
        return 0

    if a.org:
        aid, slug = a.org
        st, org = call("GET", f"/organizations/{slug}")
        if st != 200:
            sys.exit(f"no such organization '{slug}': {st}")
        st, r = call("PUT", f"/articles/{aid}",
                     {"article": {"organization_id": org["id"]}})
        if st not in (200, 201):
            sys.exit(f"routing failed: {st} {r}")
        print(f"  article {aid} -> {slug} ({org['id']})")
        print(f"  {r.get('url','')}")
        return 0

    article = pathlib.Path(a.create or a.update[1]).resolve()
    preflight(article, a.force)

    # MEASURED 2026-08-31: dev.to renders with hard breaks ON, so a source
    # wrapped at ~95 columns publishes with a <br> at every wrap. Unwrap on the
    # way out and keep the repo copy readable.
    body = article.read_text()
    if not a.no_unwrap:
        n = len(hard_wrapped(body))
        body = unwrap_article(body)
        if n:
            print(f"\nunwrapped {n} hard-wrapped paragraph(s) before posting")
    payload = {"article": {"body_markdown": body}}

    if a.create:
        st, r = call("POST", "/articles", payload)
        if st not in (200, 201):
            sys.exit(f"\ncreate failed: {st} {r}")
        print(f"\ncreated {r['id']}")
        show(r)
        if a.org_on_create:
            st, org = call("GET", f"/organizations/{a.org_on_create}")
            if st == 200:
                st, r2 = call("PUT", f"/articles/{r['id']}",
                              {"article": {"organization_id": org["id"]}})
                print(f"  routed to {a.org_on_create} ({org['id']})"
                      if st in (200, 201) else f"  routing failed: {st}")
        return 0

    aid = a.update[0]
    st, r = call("PUT", f"/articles/{aid}", payload)
    if st not in (200, 201):
        sys.exit(f"\nupdate failed: {st} {r}")
    print(f"\nupdated {aid}")
    show(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
