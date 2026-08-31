#!/usr/bin/env python3
"""Render an article cover image.

EVERY ARTICLE NEEDS A COVER. There is no path where skipping it is correct, and
nothing fails locally when you do: dev.to only fetches the `cover_image:` URL at
render time, so a missing file surfaces as a broken image on a published post.
`check-article.py` treats an absent or unreferenced cover as a hard failure.

The two destinations disagree on geometry, so this ships two modes:

    --mode devto     1376x578   2.381:1, the ratio dev.to actually displays;
                                text is fine here
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

# MEASURED 2026-08-31: dev.to does not display a cover at the size you upload. Its
# proxy renders width=1000,height=420,fit=cover -- a 2.381:1 CENTRE CROP. A
# 1376x768 cover (1.79:1) therefore loses 95px off the top and 95px off the bottom:
# the eyebrow was sliced through its letterforms and the footer was cut entirely,
# in every article shipped at that size.
#
# The fix is to author at the ratio that is displayed, not to nudge margins inside
# a ratio that is not. 1376x578 is 2.381:1, so fit=cover crops nothing.
MODES = {"devto": (1376, 578), "builder": (1200, 675)}

# what dev.to's proxy renders, for the geometry check and the crop simulation
DEVTO_DISPLAY = (1000, 420)

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
    k = H / 578.0  # scale the whole rhythm off the displayed height
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

    # Vertical rhythm for a 578-tall canvas. Every element sits inside it, because
    # at 2.381:1 there is no crop to hide in.
    if a.flow:
        render_flow(d, a, W, H, k)
        img = img.resize((W, H), Image.LANCZOS)
        img.save(a.out, "JPEG", quality=92, optimize=True)
        return W, H

    pad = 72 * k
    if a.eyebrow:
        draw(d, (pad, 46 * k), a.eyebrow, f(MONO, 18 * k), INK_3)

    y = 86 * k
    for line in (a.headline or "").split("|"):
        draw(d, (pad, y), line, f(SANS_B, 54 * k), INK)
        y += 64 * k

    if a.subhead:
        draw(d, (pad, y + 8 * k), a.subhead, f(SANS, 34 * k), INK_2)

    tiles = [t.split("|") for t in (a.tile or [])]
    if tiles:
        top, bot = 296 * k, 516 * k
        gap = 68 * k
        tw = (W - 2 * pad - gap) / 2
        for i, t in enumerate(tiles[:2]):
            name, sub, big, unit, claim, colour = (t + [""] * 6)[:6]
            chip = COLOURS.get(colour, COLOURS["blue"])
            x = pad + i * (tw + gap)
            d.rectangle([int(x) * S, int(top) * S, int(x + tw) * S, int(bot) * S],
                        fill=TILE_BG, outline=RULE, width=S)
            d.rectangle([int(x) * S, int(top) * S, int(x + 6) * S, int(bot) * S], fill=chip)
            draw(d, (x + 30 * k, top + 20 * k), name, f(MONO_B, 25 * k), INK)
            draw(d, (x + 30 * k, top + 52 * k), sub, f(SANS, 19 * k), INK_3)
            draw(d, (x + 30 * k, top + 82 * k), big, f(SANS_B, 62 * k), INK)
            draw(d, (x + 30 * k, top + 158 * k), unit, f(SANS, 21 * k), INK_2)
            # swatch carries identity; the words stay in ink
            d.rectangle([int(x + 30 * k) * S, int(top + 194 * k) * S,
                         int(x + 41 * k) * S, int(top + 205 * k) * S], fill=chip)
            draw(d, (x + 52 * k, top + 191 * k), claim, f(MONO_B, 18 * k), INK_2)

    if a.footer:
        d.line([int(pad) * S, int(538 * k) * S, int(W - pad) * S, int(538 * k) * S],
               fill=RULE, width=S)
        draw(d, (pad, 550 * k), a.footer, f(MONO, 18 * k), INK_3)

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


def render_flow(d, a, W, H, k):
    """One source, a toolchain, and where the artifacts land.

    A cover earns its place by saying what the article is about. Two stat tiles
    about token cost say what the SKILL costs, which is a detail inside the piece
    rather than its subject. The subject is the shape: one source file, a set of
    checks, and destinations that do not agree with each other -- and the thing
    worth seeing at a glance is which of them need a browser driven for them.

    Colour encodes exactly that, and never anything decorative:
        blue    reachable over a REST API
        orange  no API; a browser has to be driven
        muted   an API that cannot draft
    """
    # MEASURED: scaling this layout off HEIGHT alone clipped every destination
    # label at the Builder Center size, because 1200x675 is TALLER in ratio but
    # NARROWER in pixels than 1376x578. A diagram is constrained by whichever
    # dimension runs out first, so scale by the limiting one and centre what is
    # left over.
    k = min(W / 1376.0, H / 578.0)
    oy = (H - 578 * k) / 2

    def draw(dd, xy, txt, font, fill):          # shadows the module helper: adds oy
        dd.text((int(xy[0]) * S, int(xy[1] + oy) * S), txt, font=font, fill=fill, anchor="la")

    def box(x0, y0, x1, y1, **kw):
        dd = d.rounded_rectangle if "radius" in kw else d.rectangle
        dd([int(x0) * S, int(y0 + oy) * S, int(x1) * S, int(y1 + oy) * S], **kw)

    def seg(x0, y0, x1, y1, **kw):   # NOT `line`: the headline loop binds that name
        d.line([int(x0) * S, int(y0 + oy) * S, int(x1) * S, int(y1 + oy) * S], **kw)

    pad = 72 * k
    ink3, ink2, ink = INK_3, INK_2, INK

    if a.eyebrow:
        draw(d, (pad, 38 * k), a.eyebrow, f(MONO, 17 * k), ink3)
    y = 70 * k
    for line in (a.headline or "").split("|"):
        draw(d, (pad, y), line, f(SANS_B, 42 * k), ink)
        y += 50 * k
    if a.subhead:
        draw(d, (pad, y + 4 * k), a.subhead, f(SANS, 24 * k), ink2)

    top, bot = 200 * k, 500 * k
    mid = (top + bot) / 2

    # ---- source card -------------------------------------------------------
    sx, sw, sh = pad, 268 * k, 96 * k
    sy = mid - sh / 2
    name, _, cap = (a.source or "source").partition("|")
    box(sx, sy, sx + sw, sy + sh, radius=int(8 * S), fill=TILE_BG, outline=RULE, width=S)
    box(sx, sy, sx + 5 * k, sy + sh, fill=COLOURS["blue"])
    draw(d, (sx + 26 * k, sy + 26 * k), name, f(MONO_B, 22 * k), ink)
    if cap:
        draw(d, (sx + 26 * k, sy + 58 * k), cap, f(SANS, 17 * k), ink3)

    # ---- steps -------------------------------------------------------------
    steps = a.step or []
    stx, stw = sx + sw + 78 * k, 250 * k
    sth = max(len(steps) * 34 * k + 34 * k, 96 * k)
    sty = mid - sth / 2
    box(stx, sty, stx + stw, sty + sth, radius=int(8 * S), fill=SURFACE,
        outline=RULE, width=S)
    for i, st in enumerate(steps):
        ly = sty + 24 * k + i * 34 * k
        box(stx + 22 * k, ly + 7 * k, stx + 28 * k, ly + 13 * k, fill=RULE)
        draw(d, (stx + 40 * k, ly), st, f(MONO, 18 * k), ink2)

    # connector: source -> steps
    seg(sx + sw, mid, stx, mid, fill=RULE, width=S)

    # ---- destinations ------------------------------------------------------
    dests = a.dest or []
    dx = stx + stw + 96 * k
    n = len(dests)
    gap = (bot - top) / max(n, 1)
    bus = dx - 46 * k
    if n:
        first = top + gap / 2
        last = top + gap * (n - 0.5)
        seg(stx + stw, mid, bus, mid, fill=RULE, width=S)
        seg(bus, first, bus, last, fill=RULE, width=S)
    for i, spec in enumerate(dests):
        parts = (spec.split("|") + ["", "", ""])[:3]
        dname, dnote, dcol = parts
        cy = top + gap * (i + 0.5)
        colour = COLOURS.get(dcol, RULE if dcol == "muted" else COLOURS["blue"])
        seg(bus, cy, dx - 16 * k, cy, fill=RULE, width=S)
        r = 6 * k
        d.ellipse([int(dx - 10 * k - r) * S, int(cy - r + oy) * S,
                   int(dx - 10 * k + r) * S, int(cy + r + oy) * S], fill=colour)
        draw(d, (dx + 6 * k, cy - 20 * k), dname, f(SANS_B, 22 * k), ink)
        if dnote:
            draw(d, (dx + 6 * k, cy + 6 * k), dnote, f(SANS, 16 * k), ink3)

    # ---- legend ------------------------------------------------------------
    if a.legend:
        lx = pad
        ly = 534 * k
        seg(pad, 518 * k, W - pad, 518 * k, fill=RULE, width=S)
        for pair in a.legend.split(","):
            label, _, col = pair.strip().partition("|")
            colour = COLOURS.get(col, RULE)
            box(lx, ly + 4 * k, lx + 10 * k, ly + 14 * k, fill=colour)
            draw(d, (lx + 20 * k, ly), label, f(MONO, 16 * k), ink3)
            lx += (len(label) * 9.6 + 46) * k


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
    p.add_argument("--sizes",
                   help="render ONE design at several geometries, e.g. "
                        "'devto,builder'. One article has one cover; the two "
                        "sizes exist because the destinations demand them, not "
                        "because the picture should differ.")
    p.add_argument("--flow", action="store_true",
                   help="render a pipeline diagram instead of stat tiles")
    p.add_argument("--source", default="", help="--flow: 'file|caption'")
    p.add_argument("--step", action="append", help="--flow: a build step, repeatable")
    p.add_argument("--dest", action="append",
                   help="--flow: 'name|note|blue|orange|muted', repeatable")
    p.add_argument("--legend", default="", help="--flow: 'label|colour' pairs, comma separated")
    p.add_argument("--content-address", action="store_true",
                   help="name the file by a hash of its bytes, so a regenerated "
                        "cover is a URL no cache has ever seen")
    p.add_argument("--url-base",
                   help="print the cover_image: URL to paste, e.g. "
                        "https://raw.githubusercontent.com/<u>/<repo>/main/<dir>/")
    a = p.parse_args()

    # ONE design, every geometry it is needed at. Rendering each destination its
    # own picture is how a directory ends up with three covers, which is what
    # make-medium.py's alphabetical --cover fallback then picks wrongly from.
    if a.sizes:
        base = pathlib.Path(a.out)
        outs = []
        for mode in [m.strip() for m in a.sizes.split(",") if m.strip()]:
            if mode not in MODES:
                sys.exit(f"unknown size '{mode}'; known: {', '.join(sorted(MODES))}")
            sub = argparse.Namespace(**vars(a))
            sub.sizes = None
            sub.mode = mode
            sub.with_text = True          # one design means text at every size
            sub.no_text = False
            sub.out = str(base if mode == "devto"
                          else base.with_name(f"{base.stem}-{mode}{base.suffix}"))
            w, h = render(sub)
            if sub.content_address:
                sub.out = str(content_address(pathlib.Path(sub.out)))
            kb = os.path.getsize(sub.out) // 1024
            print(f"wrote {sub.out}  {w}x{h}  {kb} KB")
            if mode == "builder" and kb > 2048:
                sys.exit("FAIL: Builder Center caps cover uploads at 2 MB")
            outs.append(sub.out)
        if a.url_base:
            for o in outs:
                print(f"  {a.url_base.rstrip('/')}/{pathlib.Path(o).name}")
        print("\nAWS's editor says text in images is not recommended. This is one "
              "cover at two sizes\nby choice: a different picture per destination "
              "is a third thing to keep in step.")
        return 0

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
