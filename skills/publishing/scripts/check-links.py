#!/usr/bin/env python3
"""Fetch every URL the destinations will fetch, and compare the bytes to disk.

Every other check in this kit reasons about local state: is the file there, is it
tracked, does it match HEAD. Each of those was fooled at least once, because local
state is not what the destination sees:

  * a cover was tracked, so `ls-files` passed -- and the published URL served an
    older image, because it had been regenerated after its commit
  * a hosted HTML pointed at the right DIRECTORY NAME in the wrong REPOSITORY, so
    the pre-flight's path check passed and every <img> would have 404'd
  * a push propagated, and raw.githubusercontent still served the previous bytes
    from cache for several minutes

The only check that cannot be fooled is fetching the URL and comparing what comes
back. That is this script. It is slower and it needs the network, which is why it
is separate from check-article.py rather than inside it.

    check-links.py <article>.md [--pinned] [--timeout 20]

--pinned resolves raw.githubusercontent URLs at HEAD's commit sha instead of the
branch, which bypasses the CDN's branch cache. Use it right after a push, when the
branch URL can legitimately lag; without it you are testing what a reader gets now.
"""

import argparse
import hashlib
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

FAILS, WARNS = [], []


def fail(m):
    FAILS.append(m); print(f"  FAIL  {m}")


def warn(m):
    WARNS.append(m); print(f"  WARN  {m}")


def ok(m):
    print(f"  ok    {m}")


def head_sha(d):
    return subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def fetch(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "publishing-kit"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return 0, str(e).encode()


def local_for(url, d):
    """Map a raw.githubusercontent URL back to the file it should be serving."""
    m = re.search(r"/main/(?:.*/)?" + re.escape(d.name) + r"/(.+)$", url)
    if not m:
        m = re.search(r"/[0-9a-f]{40}/(?:.*/)?" + re.escape(d.name) + r"/(.+)$", url)
    return (d / m.group(1)) if m else None


def check(url, d, timeout, pinned_sha):
    shown = url
    if pinned_sha:
        url = re.sub(r"(raw\.githubusercontent\.com/[^/]+/[^/]+)/main/",
                     rf"\1/{pinned_sha}/", url)
    status, body = fetch(url, timeout)
    # the cover appears at two URLs -- the article directory and medium/img -- so
    # print enough path to tell them apart. Two identical-looking ok lines for
    # different URLs is a report that hides a difference.
    parts = shown.rstrip("/").split("/")
    name = "/".join(parts[-2:]) if parts[-2] in ("img", "medium") else parts[-1]
    if status != 200:
        fail(f"{name}: HTTP {status}")
        return
    f = local_for(shown, d)
    if f is None or not f.exists():
        warn(f"{name}: HTTP 200, no local file to compare against")
        return
    served = hashlib.sha256(body).hexdigest()[:16]
    ondisk = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    if served == ondisk:
        ok(f"{name}: HTTP 200, bytes match disk")
    else:
        fail(f"{name}: HTTP 200 but the served bytes differ from disk "
             f"(served {served}, disk {ondisk}) -- unpushed, or a stale CDN copy")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--pinned", action="store_true",
                    help="resolve at HEAD's sha, bypassing the branch CDN cache")
    ap.add_argument("--timeout", type=int, default=20)
    a = ap.parse_args()

    src = pathlib.Path(a.article).resolve()
    d = src.parent
    text = src.read_text()
    sha = head_sha(d) if a.pinned else ""

    print(f"\n{src.name}" + (f"  (pinned at {sha[:7]})" if sha else "  (branch URLs)"))

    urls = []
    m = re.search(r"^cover_image:\s*(\S+)", text, re.M)
    if m:
        urls.append(m.group(1))
    else:
        warn("no cover_image: to check")

    for h in sorted((d / "medium").glob("*-hosted.html")) if (d / "medium").exists() else []:
        urls += re.findall(r'src="(https://[^"]+)"', h.read_text())

    seen = set()
    for u in urls:
        if u not in seen:
            seen.add(u)
            check(u, d, a.timeout, sha)

    links = d / "links.txt"
    if links.exists():
        for ln in links.read_text().splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, _, v = ln.partition("=")
            v = v.strip()
            if v.upper() == "PENDING" or not v:
                warn(f"links.txt {k.strip()}: PENDING")
            elif "temp-slug" in v:
                warn(f"links.txt {k.strip()}: draft URL, the slug changes on publish")
            else:
                st, _ = fetch(v, a.timeout)
                (ok if st == 200 else fail)(f"links.txt {k.strip()}: HTTP {st}")

    print(f"\n{len(FAILS)} fail, {len(WARNS)} warn")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
