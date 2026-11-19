#!/usr/bin/env python3
"""Cover for the LinkedIn article walk-through: a page passing through a screen.

Textless, in the kit's palette (make-cover.py: surface, paper, blue, orange).
Left, the page as written: two heading sizes plus a third, an inline-code chip,
a nested list, a table. Centre, a screen. Right, the page the editor saves: a
cover slot, two heading sizes, plain lines. Under the screen, what stayed behind.

    python3 make_cover.py            # writes cover.<hash>.jpg and cover-builder.<hash>.jpg
"""
import hashlib
import pathlib

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SURFACE = (26, 26, 25)
PAPER = (236, 234, 224)
LINE = (176, 174, 164)
DARK = (92, 91, 86)
BLUE = (57, 135, 229)
ORANGE = (217, 89, 38)
MUTED = (128, 127, 120)
S = 2  # draw at 2x, downsample


def page(d, x, y, w, h, r=10):
    d.rounded_rectangle((x, y, x + w, y + h), r * S, fill=PAPER)


def bar(d, x, y, w, h, c):
    d.rounded_rectangle((x, y, x + w, y + h), h // 2, fill=c)


def render(W, H):
    img = Image.new("RGB", (W * S, H * S), SURFACE)
    glow = Image.new("RGB", img.size, (0, 0, 0))
    g = ImageDraw.Draw(glow)
    u = H * S / 578  # one design unit
    pw, ph = int(250 * u), int(350 * u)
    cy = H * S // 2
    lx = int(W * S * 0.16)
    rx = int(W * S * 0.84) - pw
    top = cy - ph // 2
    sx = W * S // 2

    # soft light behind both pages and the screen
    for x in (lx, rx):
        g.rounded_rectangle((x - 8 * u, top - 8 * u, x + pw + 8 * u, top + ph + 8 * u), 24, fill=(40, 40, 38))
    g.rectangle((sx - 5 * u, top - 34 * u, sx + 5 * u, top + ph + 34 * u), fill=(20, 60, 110))
    img = ImageChops.add(img, glow.filter(ImageFilter.GaussianBlur(22 * u)))
    d = ImageDraw.Draw(img)

    # ---- left: the page as written
    page(d, lx, top, pw, ph)
    m = int(26 * u)
    x0, y = lx + m, top + int(30 * u)
    inner = pw - 2 * m
    bar(d, x0, y, int(inner * 0.72), int(20 * u), DARK); y += int(40 * u)          # big heading
    bar(d, x0, y, inner, int(9 * u), LINE); y += int(20 * u)
    bar(d, x0, y, int(inner * 0.34), int(9 * u), LINE)
    bar(d, x0 + int(inner * 0.38), y - int(3 * u), int(inner * 0.30), int(15 * u), ORANGE)  # inline code
    bar(d, x0 + int(inner * 0.72), y, int(inner * 0.2), int(9 * u), LINE); y += int(34 * u)
    bar(d, x0, y, int(inner * 0.5), int(14 * u), DARK); y += int(30 * u)           # mid heading
    for ind, wd in ((0, 0.8), (0.14, 0.6), (0.14, 0.5), (0, 0.7)):                 # nested list
        d.ellipse((x0 + inner * ind, y, x0 + inner * ind + 9 * u, y + 9 * u), fill=BLUE)
        bar(d, x0 + int(inner * ind) + int(18 * u), y, int(inner * wd) - int(18 * u), int(9 * u), LINE)
        y += int(20 * u)
    y += int(8 * u)
    bar(d, x0, y, int(inner * 0.36), int(10 * u), MUTED); y += int(24 * u)         # small heading
    gh = top + ph - int(26 * u) - y                                                # table
    for r in range(4):
        for c in range(3):
            cw, ch = inner / 3, gh / 4
            d.rectangle((x0 + c * cw, y + r * ch, x0 + (c + 1) * cw - 3 * u, y + (r + 1) * ch - 3 * u),
                        outline=DARK if r else ORANGE, width=max(2, int(2 * u)))

    # ---- centre: the screen, with motion lines through it
    for i in range(15):
        yy = top - int(30 * u) + i * (ph + int(60 * u)) / 14
        d.rounded_rectangle((sx - 5 * u, yy - 9 * u, sx + 5 * u, yy + 9 * u), int(5 * u), fill=BLUE)
    for yy in (cy - 96 * u, cy - 32 * u, cy + 32 * u):
        for x1, x2 in ((lx + pw + 26 * u, sx - 26 * u), (sx + 26 * u, rx - 26 * u)):
            d.line((x1, yy, x2, yy), fill=(70, 70, 66), width=max(2, int(3 * u)))
    # what stays behind, at the foot of the screen
    fy = top + ph + int(8 * u)
    bar(d, sx - int(86 * u), fy, int(52 * u), int(15 * u), ORANGE)
    for c in range(3):
        d.rectangle((sx - 22 * u + c * 22 * u, fy - 4 * u, sx - 22 * u + (c + 1) * 22 * u - 3 * u, fy + 16 * u),
                    outline=MUTED, width=max(2, int(2 * u)))
    bar(d, sx + int(54 * u), fy + int(3 * u), int(40 * u), int(10 * u), MUTED)

    # ---- right: the page the editor saves
    page(d, rx, top, pw, ph)
    x0, y = rx + m, top + int(26 * u)
    d.rounded_rectangle((x0, y, x0 + inner, y + int(inner * 9 / 16)), int(6 * u), fill=BLUE)   # 16:9 cover
    y += int(inner * 9 / 16) + int(24 * u)
    bar(d, x0, y, int(inner * 0.72), int(20 * u), DARK); y += int(38 * u)
    for wd in (1.0, 0.86):
        bar(d, x0, y, int(inner * wd), int(9 * u), LINE); y += int(20 * u)
    y += int(8 * u)
    bar(d, x0, y, int(inner * 0.5), int(14 * u), DARK); y += int(30 * u)
    for wd in (0.8, 0.6, 0.7):
        d.ellipse((x0, y, x0 + 9 * u, y + 9 * u), fill=BLUE)
        bar(d, x0 + int(18 * u), y, int(inner * wd) - int(18 * u), int(9 * u), LINE)
        y += int(20 * u)
    return img.resize((W, H), Image.LANCZOS)


def main():
    here = pathlib.Path(__file__).resolve().parent
    for stem, (W, H) in (("cover", (1376, 578)), ("cover-builder", (1200, 675))):
        tmp = here / f"{stem}.tmp.jpg"
        render(W, H).save(tmp, "JPEG", quality=90, optimize=True)
        h = hashlib.sha256(tmp.read_bytes()).hexdigest()[:8]
        out = here / f"{stem}.{h}.jpg"
        tmp.replace(out)
        print(f"wrote {out.name}  {W}x{H}  {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
