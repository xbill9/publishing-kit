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
                             file renders as a broken image -- and a tracked file
                             that was REGENERATED after its commit serves the old
                             image, so HEAD is compared, not just tracking
  4. COVER GEOMETRY          2.381:1 for dev.to, which is what its proxy shows;
                             FAILS when ink falls in the band it would crop
  4b. CONTENT ADDRESSING     a hashed filename must still match its bytes, and a
                             cover without one is warned about: dev.to proxies the
                             URL rather than re-hosting, so reusing a name puts two
                             images behind one address
  5. PUBLISHED FALSE         never ship `published: true` by accident
  6. FRONT MATTER            title, description, tags present
  7. MEDIUM ARTIFACTS        if medium/ exists, its images are present and its
                             hosted HTML points at THIS article's directory
  8. NO EMPTY LINKS          `](  )` and bare `](#)` are dead on arrival
"""

import argparse
import hashlib
import pathlib
import re
import subprocess
import sys

from bodytext import hard_wrapped

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


HASHED = re.compile(r"^(?P<stem>.+)\.(?P<hash>[0-9a-f]{8})(?P<ext>\.[A-Za-z0-9]+)$")


def content_address_ok(path):
    """For a content-addressed cover, does the name still describe the bytes?

    Returns None when the filename carries no hash, so this stays optional. A
    mismatch means the file was regenerated or edited without renaming, which puts
    the old bytes and the new bytes behind one URL -- the thing content addressing
    exists to prevent.
    """
    m = HASHED.match(path.name)
    if not m:
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8] == m.group("hash")


# MEASURED 2026-08-31: dev.to does not show the cover you upload. Its proxy renders
# `width=1000,height=420,fit=cover` -- a 2.381:1 CENTRE CROP. A 1376x768 cover loses
# 95px off the top and 95px off the bottom, which sliced the eyebrow through its
# letterforms and cut the footer entirely, in every article shipped at that size.
DEVTO_RATIO = 1000 / 420


def check_devto_crop(im, w, h):
    """Would dev.to's crop cut anything that was drawn?"""
    ratio = w / h
    if abs(ratio - DEVTO_RATIO) < 0.02:
        ok(f"geometry {w}x{h} is dev.to's displayed 2.381:1; nothing is cropped")
        return

    visible_h = w / DEVTO_RATIO
    if visible_h >= h:
        warn(f"geometry {w}x{h} ({ratio:.2f}:1) is wider than dev.to's 2.381:1; "
             f"it will be cropped left and right")
        return

    cut = int((h - visible_h) / 2)
    rgb = im.convert("RGB")
    bg = rgb.getpixel((1, 1))

    def ink(band):
        return sum(1 for px in band
                   if max(abs(px[i] - bg[i]) for i in range(3)) > 30)

    top = ink(list(rgb.crop((0, 0, w, cut)).getdata()))
    bot = ink(list(rgb.crop((0, h - cut, w, h)).getdata()))
    where = f"{cut}px off the top and bottom"
    if top or bot:
        fail(f"geometry {w}x{h}: dev.to crops {where} and there is content there "
             f"({top} px top, {bot} px bottom). Author at 2.381:1 -- "
             f"make-cover.py --mode devto now emits 1376x578")
    else:
        warn(f"geometry {w}x{h}: dev.to crops {where}, though nothing is drawn there")


def matches_head(root, path):
    """Tracked is not enough: a REGENERATED cover is tracked and still wrong.

    MEASURED: a cover regenerated after its commit passed `ls-files` while the
    published URL still served the old image -- the exact failure check 3 exists
    to prevent, one step further along. Compare against HEAD, not the index.
    """
    try:
        r = subprocess.run(["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", str(path)],
                           capture_output=True)
        return r.returncode == 0
    except Exception:
        return True


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
            elif not matches_head(root, f):
                fail(f"{name} differs from HEAD -- it was regenerated after its "
                     f"commit, so the published URL still serves the old image")
            else:
                ok(f"{name} is committed and matches HEAD")
            ca = content_address_ok(f)
            if ca is None:
                warn(f"{name} is not content-addressed; a regenerated cover reuses "
                     f"this URL, and dev.to proxies it rather than re-hosting")
            elif ca:
                ok(f"{name} hash matches its bytes")
            else:
                fail(f"{name} carries a hash that no longer matches its bytes -- "
                     f"regenerate with --content-address, do not edit in place")
            try:
                from PIL import Image
                im = Image.open(f)
                w, h = im.size
                check_devto_crop(im, w, h)
            except ImportError:
                warn("Pillow not installed; skipped geometry check")
    if covers and not m:
        warn(f"found {covers[0].name} on disk but nothing references it")

    # 4c  ONE ARTICLE, ONE COVER ----------------------------------------------
    # An article published to several destinations is ONE piece and wants one
    # cover. Giving each destination its own picture is three things to keep in
    # step instead of one, and it is what leaves a directory holding several
    # *cover*.jpg for make-medium.py's alphabetical fallback to choose wrongly
    # from. Nothing here checked it, and this repo shipped three covers for one
    # article without a single check going red.
    siblings = sorted(x for x in d.glob("*.md")
                      if x != src and re.search(r"^cover_image:", x.read_text(), re.M))
    if siblings and m:
        mine = m.group(1).rstrip("/").split("/")[-1]
        others = {}
        for sib in siblings:
            sm = re.search(r"^cover_image:\s*(\S+)", front_matter(sib.read_text()), re.M)
            if sm:
                others[sib.name] = sm.group(1).rstrip("/").split("/")[-1]
        differing = {k: v for k, v in others.items() if v != mine}
        if differing:
            fail(f"sibling version(s) reference a different cover: "
                 f"{', '.join(f'{k} -> {v}' for k, v in differing.items())}. "
                 f"One article, one cover -- render it at each geometry with "
                 f"make-cover.py --sizes")
        else:
            ok(f"all {len(others) + 1} version(s) share one cover")

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
        imgdir = med / "img"
        imgs = sorted(f for f in imgdir.iterdir()
                      if f.suffix.lower() in (".png", ".jpg", ".jpeg")
                      ) if imgdir.exists() else []
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
                fail(f"{h.name} references {len(missing)} missing image(s): {missing[:3]}")
        if imgs:
            untracked = [i.name for i in imgs if not tracked(root, i)]
            stale = [i.name for i in imgs if tracked(root, i) and not matches_head(root, i)]
            if untracked:
                fail(f"{len(untracked)} medium/img image(s) not committed: {untracked[:3]}")
            if stale:
                fail(f"{len(stale)} medium/img image(s) regenerated since their "
                     f"commit, so the pushed copies are stale: {stale[:3]}")
            if not untracked and not stale:
                ok(f"{len(imgs)} medium/img image(s) committed and matching HEAD")

    # 7b  HARD WRAPS ---------------------------------------------------------
    # MEASURED 2026-08-31: dev.to renders with hard breaks ON -- 47 of 62
    # paragraphs in a published article carried <br>, from a source with no
    # explicit line breaks at all. Builder Center does the same on paste. This
    # was described as a Builder Center quirk for months because that is where
    # someone happened to look.
    hw = hard_wrapped(text)
    if hw:
        warn(f"{len(hw)} hard-wrapped paragraph(s) render with a line break at "
             f"every wrap; publish-devto.py unwraps, a manual paste does not "
             f"(first at line {hw[0][0]})")
    else:
        ok("no hard-wrapped paragraphs")

    # 7c  COUNTS OF THE KIT'S OWN PARTS ---------------------------------------
    # An article about a toolchain that states how many scripts it has is stating
    # a figure the toolchain's own growth invalidates. This drifted three times:
    # "five scripts" became nine, "Twelve scripts, four reference files" became
    # fourteen and six. house-style.md forbids it; this makes the rule checkable.
    WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
             "twelve": 12, "thirteen": 13, "fourteen": 14, "a dozen": 12}
    skill_dir = next((p for p in (d, *d.parents)
                      if (p / "skills" / "publishing" / "scripts").is_dir()), None)
    if skill_dir:
        real = {
            "scripts": len(list((skill_dir / "skills/publishing/scripts").glob("*.py"))),
            "reference files": len(list((skill_dir / "skills/publishing/references").glob("*.md"))),
        }
        bad = []
        for noun, actual in real.items():
            # Two bugs found by positive controls, both of which made this check
            # pass on the thing it exists to catch:
            #   1. no adjective slot, so "twelve SMALL scripts" was missed
            #   2. a generic [A-Za-z]+ count slot, which matched "AND twelve
            #      small scripts" -- the earlier position wins, group is "and",
            #      and the real number is never examined
            # Match number words explicitly, and allow adjectives after them.
            numbers = "|".join(sorted(WORDS, key=len, reverse=True)) + r"|\d+"
            pat = rf"\b({numbers})\s+(?:\w+\s+){{0,2}}{noun}\b"
            for m in re.finditer(pat, text, re.I):
                raw = m.group(1).lower()
                n = WORDS.get(raw, int(raw) if raw.isdigit() else None)
                if n is not None and n != actual:
                    bad.append(f"'{m.group(0)}' but there are {actual}")
        if bad:
            fail(f"stale count of the kit's own parts: {'; '.join(bad[:3])}. "
                 f"Derive it from skill-footprint.py or leave it out of prose")
        else:
            ok("no stale counts of the kit's own parts")

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
