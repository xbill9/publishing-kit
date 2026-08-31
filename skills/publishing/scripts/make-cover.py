#!/usr/bin/env python3
"""Render an article cover image.

EVERY ARTICLE NEEDS A COVER. There is no path where skipping it is correct, and
nothing fails locally when you do: dev.to only fetches the `cover_image:` URL at
render time, so a missing file surfaces as a broken image on a published post.
`check-article.py` treats an absent or unreferenced cover as a hard failure.

The two destinations disagree on geometry, so this ships two modes:

    --mode devto     1376x768   text is fine; this is the house size
    --mode builder   1200x675   AWS Builder Center's recommended size, max 2 MB.
                                Their editor says "Text in images is not
                                recommended", so this mode defaults to --no-text.

Layout is a stat-tile pair: a headline plus up to two tiles whose whole job is to
show two numbers that disagree. Colour does IDENTITY work only, so it rides on a
chip and a swatch -- numerals and labels wear ink tokens, never the series colour.
The palette is categorical slots 1 and 2 of the validated dark set, checked with
the dataviz validator rather than eyeballed (CVD dE 26.8 protan, normal-vision
dE 31.8, contrast PASS on surface #1a1a19).

Usage:
    make-cover.py --out devto-cover.jpg \\
      --eyebrow "GEMMA 4 E2B - vLLM 0.28.0 - AWS EC2" \\
      --headline "The cheapest CUDA GPU|on AWS has an Arm CPU." \\
      --subhead  "You probably want the Intel one." \\
      --tile "g5g.xlarge|Graviton2 - NVIDIA T4G|\\$0.42|per hour|CHEAPEST PER HOUR|orange" \\
      --tile "g4dn.xlarge|Intel - NVIDIA T4|\\$0.603|per M output tokens|CHEAPEST PER TOKEN|blue" \\
      --footer "Same GPU either way: SM 7.5 - 15,360 MiB - 320.1 GB/s"

`--headline` splits on `|` into lines. Each `--tile` is
name|sub|number|unit|claim|colour, colour being `blue` or `orange`.
"""

import argparse
import hashlib
import os
import pathlib
import re
import sys

from PIL import Image, ImageDraw, ImageFont

S = 2  # supersample, then downsample -- otherwise the type looks soft

MODES = {"devto": (1376, 768), "builder": (1200, 675)}

SURFACE = (26, 26, 25)      # #1a1a19  validated dark chart surface
TILE_BG = (32, 32, 31)
INK = (255, 255, 255)       # text-primary
INK_2 = (195, 194, 183)     # text-secondary
INK_3 = (128, 127, 120)     # muted
RULE = (58, 58, 55)
COLOURS = {"blue": (57, 135, 229), "orange": (217, 89, 38)}

SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"
MONO_B = "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"


def f(path, size):
    return ImageFont.truetype(path, max(8, int(size * S)))


def draw(d, xy, s, font, fill):
    d.text((int(xy[0]) * S, int(xy[1]) * S), s, font=font, fill=fill, anchor="la")


def render(a):
    W, H = MODES[a.mode]
    k = H / 768.0  # scale the whole rhythm off the reference height
    img = Image.new("RGB", (W * S, H * S), SURFACE)
    d = ImageDraw.Draw(img)

    # subtle vignette so a flat fill does not read as a slide
    n = int(80 * k)
    for i in range(n):
        v = int(6 * (1 - i / n))
        d.rectangle([i * S, i * S, (W - i) * S, (H - i) * S],
                    outline=(SURFACE[0] + v, SURFACE[1] + v, SURFACE[2] + v), width=S)

    if a.no_text:
        # Builder Center discourages text in cover images, so this says the same
        # thing with marks: a bar pair anchored to a baseline reads as "two
        # quantities compared" without asserting a number. Heights come from
        # --ratio so the picture is not lying about which one is larger.
        #
        # ORDER MATTERS: --ratio is first:second and maps to orange:blue, the
        # same order as the two --tile arguments. Pass them in the SAME order
        # as the article's tiles or the taller bar will be the wrong subject.
        base = H * 0.80
        top_y = H * 0.20
        span = base - top_y
        bw = W * 0.20
        gap = W * 0.12
        pad_x = (W - (2 * bw + gap)) / 2  # centre the pair
        d.line([int(pad_x - bw * 0.35) * S, int(base) * S,
                int(W - pad_x + bw * 0.35) * S, int(base) * S], fill=RULE, width=2 * S)
        try:
            r1, r2 = (float(x) for x in a.ratio.split(":"))
        except Exception:
            r1, r2 = 1.0, 0.62
        hi = max(r1, r2)
        for i, (r, colour) in enumerate(((r1, "orange"), (r2, "blue"))):
            x0 = pad_x + i * (bw + gap)
            h = span * (r / hi)
            y0 = base - h
            # 4px rounded data-end, anchored square to the baseline
            d.rounded_rectangle([int(x0) * S, int(y0) * S, int(x0 + bw) * S, int(base) * S],
                                radius=int(6 * S), fill=COLOURS[colour])
            d.rectangle([int(x0) * S, int(base - 8) * S, int(x0 + bw) * S, int(base) * S],
                        fill=COLOURS[colour])
        img = img.resize((W, H), Image.LANCZOS)
        img.save(a.out, "JPEG", quality=92, optimize=True)
        return W, H

    pad = 88 * k
    y = 84 * k
    if a.eyebrow:
        draw(d, (pad, y), a.eyebrow, f(MONO, 19 * k), INK_3)

    y = 128 * k
    for line in (a.headline or "").split("|"):
        draw(d, (pad, y), line, f(SANS_B, 62 * k), INK)
        y += 72 * k

    if a.subhead:
        draw(d, (pad, y + 12 * k), a.subhead, f(SANS, 40 * k), INK_2)

    tiles = [t.split("|") for t in (a.tile or [])]
    if tiles:
        top, bot = 372 * k, 648 * k
        gap = 76 * k
        tw = (W - 2 * pad - gap) / 2
        for i, t in enumerate(tiles[:2]):
            name, sub, big, unit, claim, colour = (t + [""] * 6)[:6]
            chip = COLOURS.get(colour, COLOURS["blue"])
            x = pad + i * (tw + gap)
            d.rectangle([int(x) * S, int(top) * S, int(x + tw) * S, int(bot) * S],
                        fill=TILE_BG, outline=RULE, width=S)
            d.rectangle([int(x) * S, int(top) * S, int(x + 6) * S, int(bot) * S], fill=chip)
            draw(d, (x + 34 * k, top + 26 * k), name, f(MONO_B, 27 * k), INK)
            draw(d, (x + 34 * k, top + 62 * k), sub, f(SANS, 20 * k), INK_3)
            draw(d, (x + 34 * k, top + 98 * k), big, f(SANS_B, 72 * k), INK)
            draw(d, (x + 34 * k, top + 190 * k), unit, f(SANS, 22 * k), INK_2)
            # swatch carries identity; the words stay in ink
            d.rectangle([int(x + 34 * k) * S, int(top + 234 * k) * S,
                         int(x + 46 * k) * S, int(top + 246 * k) * S], fill=chip)
            draw(d, (x + 58 * k, top + 231 * k), claim, f(MONO_B, 19 * k), INK_2)

    if a.footer:
        d.line([int(pad) * S, int(686 * k) * S, int(W - pad) * S, int(686 * k) * S],
               fill=RULE, width=S)
        draw(d, (pad, 710 * k), a.footer, f(MONO, 20 * k), INK_3)

    img = img.resize((W, H), Image.LANCZOS)
    img.save(a.out, "JPEG", quality=92, optimize=True)
    return W, H


# A cover URL is a MUTABLE NAME, and both destinations that fetch one treat it as
# permanent. MEASURED 2026-08-31: dev.to does not re-host a cover, it proxies it --
# `media2.dev.to/dynamic/image/.../<urlencoded source URL>` -- so the source URL is
# embedded in the published article for its lifetime, and a proxy keyed on that URL
# decides for itself when to look again. Regenerating a cover in place therefore
# means an article whose cover may or may not be the one you just made, and a
# filename reused across articles silently repaints the older one.
#
# Same reasoning as `references/medium.md` gives for the importer's URL cache: a
# content-addressed filename is always a URL nothing has cached, and the old file
# stays put so already-published articles keep rendering.
HASHED = re.compile(r"^(?P<stem>.+)\.(?P<hash>[0-9a-f]{8})(?P<ext>\.[A-Za-z0-9]+)$")


def content_hash(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()[:8]


def content_address(out):
    """Rename to <stem>.<sha8><ext>, stripping any hash already there."""
    m = HASHED.match(out.name)
    stem, ext = (m.group("stem"), m.group("ext")) if m else (out.stem, out.suffix)
    target = out.with_name(f"{stem}.{content_hash(out)}{ext}")
    if target != out:
        if target.exists():
            target.unlink()
        out.rename(target)
    return target


def main():
    p = argparse.ArgumentParser(description="Render an article cover image")
    p.add_argument("--out", required=True)
    p.add_argument("--mode", choices=sorted(MODES), default="devto")
    p.add_argument("--eyebrow", default="")
    p.add_argument("--headline", default="")
    p.add_argument("--subhead", default="")
    p.add_argument("--tile", action="append",
                   help="name|sub|number|unit|claim|blue-or-orange (max 2)")
    p.add_argument("--footer", default="")
    p.add_argument("--ratio", default="1:0.62",
                   help="bar heights for --no-text covers as orange:blue, matching --tile order, e.g. 168:242")
    p.add_argument("--no-text", action="store_true",
                   help="abstract cover, no type (default for --mode builder)")
    p.add_argument("--with-text", action="store_true",
                   help="force type on in builder mode, against AWS guidance")
    p.add_argument("--content-address", action="store_true",
                   help="name the file by a hash of its bytes, so a regenerated "
                        "cover is a URL no cache has ever seen")
    p.add_argument("--url-base",
                   help="print the cover_image: URL to paste, e.g. "
                        "https://raw.githubusercontent.com/<u>/<repo>/main/<dir>/")
    a = p.parse_args()
    if a.mode == "builder" and not a.with_text:
        a.no_text = True
    w, h = render(a)
    out = pathlib.Path(a.out)

    if a.content_address:
        out = content_address(out)
        a.out = str(out)

    kb = os.path.getsize(a.out) // 1024
    print(f"wrote {a.out}  {w}x{h}  {kb} KB")
    if a.url_base:
        print(f"cover_image: {a.url_base.rstrip('/')}/{out.name}")
    if a.mode == "builder" and kb > 2048:
        sys.exit("FAIL: Builder Center caps cover uploads at 2 MB")


if __name__ == "__main__":
    main()
