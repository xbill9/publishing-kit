#!/usr/bin/env python3
"""Pre-flight an article before publishing. Exits non-zero on any FAIL.

Everything checked here has actually shipped broken at least once. The checks are
ordered by how silently each one fails -- the cover is first because nothing
whatsoever errors locally when it is missing.

    check-article.py devto-my-article.md [--repo-root .]

Checks:
  1. COVER EXISTS            every article needs one, no exceptions
  2. COVER REFERENCED        cover_image: front matter present and pointing at it
  3. COVER COMMITTED         the URL is fetched at render time, so an uncommitted
                             or unpushed file renders as a broken image
  4. COVER GEOMETRY          1376x768 for dev.to; warn otherwise
  5. PUBLISHED FALSE         never ship `published: true` by accident
  6. FRONT MATTER            title, description, tags present
  7. MEDIUM ARTIFACTS        if medium/ exists, its images are present and its
                             hosted HTML points at THIS article's directory
  8. NO EMPTY LINKS          `](  )` and bare `](#)` are dead on arrival
"""

import argparse
import pathlib
import re
import subprocess
import sys

FAILS = []
WARNS = []


def fail(msg):
    FAILS.append(msg)
    print(f"  FAIL  {msg}")


def warn(msg):
    WARNS.append(msg)
    print(f"  WARN  {msg}")


def ok(msg):
    print(f"  ok    {msg}")


def front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else ""


def tracked(root, path):
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", str(path)],
                           capture_output=True)
        return r.returncode == 0
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--repo-root", default=".")
    a = ap.parse_args()

    src = pathlib.Path(a.article).resolve()
    root = pathlib.Path(a.repo_root).resolve()
    d = src.parent
    text = src.read_text()
    fm = front_matter(text)

    print(f"\n{src.name}")

    # 1-4  COVER --------------------------------------------------------------
    m = re.search(r"^cover_image:\s*(\S+)", fm, re.M)
    covers = sorted(list(d.glob("*cover*.jpg")) + list(d.glob("*cover*.png")))
    if not m:
        fail("no cover_image: in front matter -- every article needs a cover")
    else:
        url = m.group(1)
        name = url.rstrip("/").split("/")[-1]
        f = d / name
        if not f.exists():
            fail(f"cover_image points at {name}, which does not exist in {d.name}/ "
                 f"(nothing errors locally; it breaks once published)")
        else:
            ok(f"cover present: {name}")
            if not tracked(root, f):
                fail(f"{name} is not committed -- the URL is fetched at render "
                     f"time, so it must be pushed before publishing")
            else:
                ok(f"{name} is tracked by git")
            try:
                from PIL import Image
                w, h = Image.open(f).size
                if (w, h) == (1376, 768):
                    ok(f"geometry {w}x{h}")
                else:
                    warn(f"geometry {w}x{h}; dev.to house size is 1376x768")
            except ImportError:
                warn("Pillow not installed; skipped geometry check")
    if covers and not m:
        warn(f"found {covers[0].name} on disk but nothing references it")

    # 5  PUBLISHED ------------------------------------------------------------
    if re.search(r"^published:\s*true", fm, re.M):
        fail("published: true -- default to false and publish deliberately")
    elif re.search(r"^published:\s*false", fm, re.M):
        ok("published: false")
    else:
        warn("no published: field")

    # 6  FRONT MATTER ---------------------------------------------------------
    for k in ("title", "description", "tags"):
        if re.search(rf"^{k}:\s*\S", fm, re.M):
            ok(f"{k} present")
        else:
            fail(f"{k} missing from front matter")

    # 7  MEDIUM ARTIFACTS -----------------------------------------------------
    med = d / "medium"
    if med.exists():
        hosted = sorted(med.glob("*-hosted.html"))
        imgs = sorted((med / "img").glob("*.png")) if (med / "img").exists() else []
        if not hosted:
            warn("medium/ exists but has no -hosted.html")
        for h in hosted:
            refs = re.findall(r'src="(https://[^"]+/medium/img/[^"]+)"', h.read_text())
            if refs:
                seg = refs[0].split("/medium/img/")[0].rstrip("/").split("/")[-1]
                if seg != d.name:
                    fail(f"{h.name} points <img> at '{seg}/medium/img' but this "
                         f"article lives in '{d.name}' -- those URLs 404")
                else:
                    ok(f"{h.name} image URLs resolve to {d.name}")
            missing = [r.split("/")[-1] for r in refs
                       if not (med / "img" / r.split("/")[-1]).exists()]
            if missing:
                fail(f"{h.name} references {len(missing)} missing PNG(s): {missing[:3]}")
        if imgs:
            untracked = [i.name for i in imgs if not tracked(root, i)]
            if untracked:
                fail(f"{len(untracked)} medium/img PNG(s) not committed: {untracked[:3]}")
            else:
                ok(f"{len(imgs)} medium/img PNG(s) committed")

    # 8  DEAD LINKS -----------------------------------------------------------
    dead = re.findall(r"\]\(\s*\)|\]\(#\)", text)
    if dead:
        fail(f"{len(dead)} empty link target(s)")
    else:
        ok("no empty link targets")

    print(f"\n{len(FAILS)} fail, {len(WARNS)} warn")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
