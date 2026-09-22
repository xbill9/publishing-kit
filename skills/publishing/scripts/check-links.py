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

It also checks every link in the article against a gate-like profile: rendered
markdown anchors are fetched with a browser User-Agent and NO cookies, and fail on
4xx/5xx or on any redirect hop through a sign-in / oauth2callback page. That is
what AWS Builder Center's "Broken Links" / "Malicious Links" gate flagged on
2026-09-15, read from its own API response; see scan_article_links(). URLs in
code blocks and plain text, and filenames that are live domains, are warnings.
"""

import argparse
import concurrent.futures
import hashlib
import pathlib
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request

from bodytext import links_path

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


# --- every link in the article, checked the way a publish gate checks it ------
#
# GROUND TRUTH, MEASURED 2026-09-15 from the gate's own API: Builder Center's
# Publish calls POST api.builder.aws.com/cs/v2/content/submit-review, then
# .../review-status, and both return
#   contentIssues.{brokenLinks,maliciousLinks,profanityDetection}.violatedFragments
# -- the exact offending URLs. The UI throws them away and shows two generic
# messages (each rendered twice; that is UI duplication, not two hits).
#
# On a draft that still failed, violatedFragments were exactly two ai.google.dev
# docs links -- listed under BOTH brokenLinks and maliciousLinks. NOT flagged:
# dev.to links (403 to a UA-less client), github.com, docs.cloud.google.com,
# py.sdk.modelcontextprotocol.io, and a URL in plain text. So the gate reads
# rendered anchors only. The likely mechanism, inferred and not confirmed: a
# cookieless client is bounced through ai.google.dev/oauth2callback and never
# gets a 200. Hence: fetch WITHOUT a cookie jar, and fail any hop through a
# sign-in or oauth2callback page.
#
# An earlier version of this check failed a URL in pasted code ending in `',`,
# an aistudio.google.com link and warned on SKILL.md, calling them "measured
# causes". They had been removed before the gate's response was captured, so
# whether the gate counted them is unknown. They are warnings now.

BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")
# A naive scanner stops at whitespace, `)` and `>` -- not at a quote or comma.
NAIVE_URL = re.compile(r"https?://[^\s)>\]<\"`]+")
TRAILING = ".,;:!?'\""
FRONT = re.compile(r"\A---\n.*?\n---\n", re.S)
FENCE = re.compile(r"^(```|~~~)[^\n]*\n.*?^\1[ \t]*$", re.M | re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")
MD_LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\((https?://[^\s)]+)(?:\s+\"[^\"]*\")?\)")
MD_IMAGE = re.compile(r"!\[[^\]\n]*\]\((https?://[^\s)]+)\)")
HTML_A = re.compile(r"<a\s[^>]*href=[\"'](https?://[^\"']+)", re.I)
AUTOLINK = re.compile(r"<(https?://[^>\s]+)>")
# Any hop, not just the final URL: ai.google.dev bounces through oauth2callback
# and may land back on the page it started from.
SIGNIN = re.compile(r"accounts\.google\.com|/oauth2callback|login\.microsoftonline\.com|"
                    r"signin\.aws|auth0\.com|okta\.com|/sign-?in\b|/log-?in\b|"
                    r"/oauth2?/auth|/sso\b|/saml", re.I)
PLACEHOLDER = re.compile(r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|"
                         r"example\.(com|org|net)|yourblog\.com)([:/]|$)", re.I)
# Builder Center's gate PASSED dev.to links that 403 a UA-less client, and Medium
# answers the same way. A 403 from them is a note, not a failure.
BOT_WALLED = re.compile(r"^https?://([\w-]+\.)*(dev\.to|medium\.com)/", re.I)
FILE_EXT = ("md|markdown|py|sh|js|mjs|ts|rs|go|rb|java|json|ya?ml|toml|ini|cfg|"
            "txt|html|css|key|pem|pb|zip|mov")
# `/` is allowed before the name: `.kiro/skills/verify-live/SKILL.md` contains
# the token SKILL.md, and excluding it hid the one live domain in a test article.
FILENAME = re.compile(rf"(?<![\w.@-])([A-Za-z0-9][\w-]*(?:\.[\w-]+)*\.(?:{FILE_EXT}))(?![\w.-])")


class _Chain(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        self.hops = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_chain(url, timeout):
    """GET with a browser UA and NO cookies; return (status, final, hops).

    No cookie jar on purpose: it is the profile the gate behaves like. With
    cookies, ai.google.dev returns 200 and the check would pass the two links the
    gate actually flagged.
    """
    chain = _Chain()
    opener = urllib.request.build_opener(chain)
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA,
                                               "Accept": "text/html,*/*"})
    try:
        with opener.open(req, timeout=timeout) as r:
            r.read(4096)
            return r.status, r.geturl(), chain.hops
    except urllib.error.HTTPError as e:
        return e.code, e.geturl() or url, chain.hops
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}", chain.hops


def resolves(name):
    try:
        socket.getaddrinfo(name, 443)
        return True
    except (socket.gaierror, UnicodeError, OSError):
        return False


def short(u, n=90):
    return u if len(u) <= n else u[:n - 1] + "…"


def verdict(url, res):
    """None when fine, else (message, bot_walled)."""
    st, final, hops = res
    signin = [h for h in hops if SIGNIN.search(h)] or ([final] if SIGNIN.search(final) else [])
    if signin and not SIGNIN.search(url):
        return (f"HTTP {st}, via a sign-in/oauth hop ({short(signin[0], 60)}) with no "
                f"cookies", False)
    if st == 0:
        return (f"no response ({final})", False)
    if st >= 400:
        return (f"HTTP {st} to a browser UA", st == 403 and bool(BOT_WALLED.match(url)))
    return None


def scan_article_links(text, timeout):
    print("\narticle links (gate profile: rendered anchors, browser UA, no cookies)")
    body = FRONT.sub("", text, count=1)          # cover_image is checked above
    prose = FENCE.sub("", body)
    anchored_text = INLINE_CODE.sub("", prose)

    anchors = []
    for rx in (MD_LINK, HTML_A, AUTOLINK):
        for u in rx.findall(anchored_text):
            if not PLACEHOLDER.match(u) and u not in anchors:
                anchors.append(u)
    images = [u for u in MD_IMAGE.findall(anchored_text) if u not in anchors]

    others, placeholders = [], 0
    for tok in NAIVE_URL.findall(body):
        clean = tok.rstrip(TRAILING)
        if PLACEHOLDER.match(tok):
            placeholders += 1
        elif tok in others:
            continue
        elif tok != clean or (clean not in anchors and clean not in images):
            # a naive cut with punctuation attached is its own token even when the
            # clean URL is also linked elsewhere -- it is what a scanner would fetch
            others.append(tok)

    wanted = list(dict.fromkeys(anchors + images +
                                [t.rstrip(TRAILING) for t in others] + others))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        res = dict(zip(wanted, ex.map(lambda u: fetch_chain(u, timeout), wanted)))

    for u in anchors:
        if "temp-slug" in u:
            warn(f"{short(u)}: dev.to draft URL, the slug changes on publish")
        v = verdict(u, res[u])
        if v is None:
            st, final, _ = res[u]
            moved = final.rstrip("/") != u.rstrip("/")
            ok(f"{short(u)}: HTTP {st}" + (f" -> {short(final, 60)}" if moved else ""))
        elif v[1]:
            warn(f"{short(u)}: {v[0]} (dev.to/Medium bot wall; Builder Center's gate passed these)")
        else:
            fail(f"{short(u)}: {v[0]} -- the shape Builder Center's gate flagged "
                 f"as broken AND malicious on ai.google.dev")

    if images:
        print("\nimage URLs (Builder Center rejects external image URLs outright; upload instead)")
        for u in images:
            v = verdict(u, res[u])
            (ok if v is None else warn)(f"{short(u)}: " + ("HTTP 200" if v is None else v[0]))

    if others:
        print("\nURLs in code blocks or plain text (the gate ignored these; warnings only)")
        for tok in others:
            url = tok.rstrip(TRAILING)
            v = verdict(url, res[url])
            if v is not None and url not in anchors:
                warn(f"{short(url)}: {v[0]}")
            if tok != url:
                # With no cookies a Google docs URL bounces through OAuth whether
                # or not the path exists, so the dead `...',` cut reads as a 302,
                # not a 404. Warn on any failed verdict, not only on 4xx.
                tv = verdict(tok, res[tok])
                if tv is not None:
                    warn(f"as a naive scanner cuts it, {short(tok)} fails ({tv[0]}) "
                         f"-- the URL runs into {tok[len(url):]!r}")
        bad = [t for t in others
               if verdict(t, res[t]) or (t.rstrip(TRAILING) not in anchors
                                         and verdict(t.rstrip(TRAILING), res[t.rstrip(TRAILING)]))]
        if not bad:
            ok(f"{len(others)} unlinked URL(s) resolve")
    if placeholders:
        ok(f"{placeholders} placeholder URL(s) skipped (localhost, example.com)")

    print("\nfilenames in the prose")
    no_urls = NAIVE_URL.sub(" ", prose)
    names = list(dict.fromkeys(FILENAME.findall(no_urls)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        live = [n for n, r in zip(names, ex.map(resolves, names)) if r]
    for n in live:
        warn(f"`{n}` in the prose resolves as a real domain (not seen flagged by a gate; "
             f"unconfirmed risk)")
    if names and not live:
        ok(f"{len(names)} filename(s) in the prose, none resolve as a domain")


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

    scan_article_links(text, a.timeout)

    links = links_path(a.article)
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
                # fetch_chain, not fetch: verdict() reads the final URL and the
                # hops, and this is the gate's profile -- browser UA, no cookies.
                st, final, hops = fetch_chain(v, a.timeout)
                # MEASURED 2026-09-16: this path failed a Medium URL with 403 in
                # one run and passed it in the next, on the same published story.
                # scan_article_links() has treated a bot wall as a note since
                # 332d2a9; links.txt did not, so the same URL was a warning in one
                # half of the run and a build failure in the other. Same rule, one
                # source: verdict() decides, here too.
                v_ = verdict(v, (st, final, hops))
                if v_ is None:
                    ok(f"links.txt {k.strip()}: HTTP {st}")
                elif v_[1]:
                    warn(f"links.txt {k.strip()}: {v_[0]} -- bot wall, not a broken "
                         f"link; open it in a browser to confirm")
                else:
                    fail(f"links.txt {k.strip()}: {v_[0]}")

    print(f"\n{len(FAILS)} fail, {len(WARNS)} warn")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
