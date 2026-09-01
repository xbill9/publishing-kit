#!/usr/bin/env python3
"""Convert a dev.to-flavoured article into Medium-ready HTML.

Medium's importer **strips markdown tables entirely** and reflows monospace
blocks, so anything that depends on alignment has to become an image. This
script finds both, renders them to PNG at 2x, and emits HTML two ways:

    <slug>-hosted.html   USE THIS ONE, for paste and for import. <img src>
                         rewritten to absolute public URLs (--img-base), which
                         Medium fetches and re-hosts. Requires the images be
                         committed AND pushed first. Measured 2026-08-31 on a
                         real paste: 7 of 7 images survived and were re-hosted
                         under Medium's 0* prefix.

    <slug>-embed.html    NEVER PASTE THIS INTO MEDIUM. Every image is inlined as
                         a base64 data: URI, and Medium silently strips data:
                         URIs on paste -- 4 of 4 images lost, measured
                         2026-08-30, with no error, no placeholder and no
                         broken-image icon. Useful only where a genuinely
                         self-contained single file is wanted for something
                         other than Medium.

    THIS DOCSTRING SAID THE OPPOSITE until 2026-08-31, describing the embed
    variant as the one to paste. The code was already right -- it prints
    "USE THIS -> hosted" and "not this -> embed" -- so the contradiction lived
    only here, where someone reading the script would have found it first.

Usage:
    ./make-medium.py article.md [outdir] [--img-base URL] [--cover FILE]

Also writes <outdir>/img/*.png so the hosted variant has something to point at.
"""

from __future__ import annotations

import base64
import html
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCALE = 2  # render at 2x for crisp display on high-DPI screens

# Liberation Sans/Mono are metric-compatible with Arial/Courier, so rendered
# tables sit next to Medium's own type without looking like a screenshot from a
# different machine. DejaVu Sans is wide and utilitarian by comparison.
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"
MONO_B = "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"

# Diagrams stay on DejaVu Sans Mono: it is the only face here with full
# box-drawing coverage, and the borders fall apart without it.
DIAGRAM_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

FG = (26, 26, 26)
MUTED = (110, 110, 110)
RULE = (208, 208, 208)
HDR_BG = (245, 245, 245)
ALT_BG = (252, 252, 252)
BG = (255, 255, 255)


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size * SCALE)


def display_width(s: str) -> int:
    return sum(
        2 if unicodedata.east_asian_width(c) in ("W", "F")
        else 0 if unicodedata.combining(c)
        else 1
        for c in s
    )


# --------------------------------------------------------------------------
# inline markdown -> (text, bold, mono) runs
# --------------------------------------------------------------------------

TOKEN = re.compile(r"(\*\*.+?\*\*|`[^`]+`)")

# DejaVu has no emoji glyphs and NotoColorEmoji is a 109px-only bitmap font, so
# emoji inside a rendered table come out as tofu. Strip them; the surrounding
# words already carry the meaning.
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF\U00002B00-\U00002BFF️⃣]+"
)


def strip_emoji(s: str) -> str:
    return re.sub(r"\s{2,}", " ", EMOJI.sub("", s)).strip()


def runs(cell: str):
    """Split a table cell into styled runs. Handles **bold** and `code`."""
    out = []
    for part in TOKEN.split(strip_emoji(cell)):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append((part[2:-2], True, False))
        elif part.startswith("`") and part.endswith("`"):
            out.append((part[1:-1], False, True))
        else:
            out.append((part, False, False))
    return out or [(cell, False, False)]


# --------------------------------------------------------------------------
# table rendering
# --------------------------------------------------------------------------

def parse_table(block: list[str]) -> tuple[list[str], list[list[str]]]:
    rows = []
    for line in block:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue  # separator
        rows.append(cells)
    return rows[0], rows[1:]


def render_table(header: list[str], body: list[list[str]], path: Path) -> None:
    fs = 15
    f_reg, f_bold = font(SANS, fs), font(SANS_B, fs)
    f_mono, f_mono_b = font(MONO, fs - 1), font(MONO_B, fs - 1)
    pad_x, pad_y = 14 * SCALE, 10 * SCALE

    probe = Image.new("RGB", (1, 1))
    d = ImageDraw.Draw(probe)

    def pick(bold: bool, mono: bool):
        if mono:
            return f_mono_b if bold else f_mono
        return f_bold if bold else f_reg

    def run_w(text: str, bold: bool, mono: bool) -> int:
        return int(d.textlength(text, font=pick(bold, mono)))

    def cell_w(cell: str, hdr: bool = False) -> int:
        # header cells render bold, which is wider than the regular face —
        # measure them the way they'll actually be drawn or the last column clips
        return sum(run_w(t, b or hdr, m) for t, b, m in runs(cell))

    ncols = len(header)
    grid = [header] + body
    widths = [
        max(
            [cell_w(header[i], True) if i < len(header) else 0]
            + [cell_w(r[i]) if i < len(r) else 0 for r in body]
        )
        + 2 * pad_x
        for i in range(ncols)
    ]
    row_h = int((fs + 12) * SCALE)
    W = sum(widths)
    H = row_h * len(grid) + 2 * SCALE

    img = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(img)

    y = 0
    for ri, row in enumerate(grid):
        is_hdr = ri == 0
        if is_hdr:
            dr.rectangle([0, y, W, y + row_h], fill=HDR_BG)
        elif ri % 2 == 0:
            dr.rectangle([0, y, W, y + row_h], fill=ALT_BG)
        x = 0
        for ci in range(ncols):
            cell = row[ci] if ci < len(row) else ""
            cx = x + pad_x
            for text, bold, mono in runs(cell):
                fnt = pick(bold or is_hdr, mono)
                col = MUTED if (mono and not is_hdr and not bold) else FG
                dr.text((cx, y + pad_y - 1 * SCALE), text, font=fnt, fill=col)
                cx += int(dr.textlength(text, font=fnt))
            x += widths[ci]
        dr.line([0, y, W, y], fill=RULE, width=SCALE)
        y += row_h
    dr.line([0, y, W, y], fill=RULE, width=SCALE)
    # header underline, heavier
    dr.line([0, row_h, W, row_h], fill=(150, 150, 150), width=SCALE)

    img.save(path)


# --------------------------------------------------------------------------
# monospace / diagram rendering
# --------------------------------------------------------------------------

def render_mono(lines: list[str], path: Path) -> None:
    fs = 13
    f = font(DIAGRAM_MONO, fs)
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    ch = probe.textlength("M", font=f)
    line_h = int(fs * 1.45 * SCALE)
    pad = 18 * SCALE

    cols = max(display_width(l) for l in lines)
    W = int(cols * ch) + 2 * pad
    H = line_h * len(lines) + 2 * pad

    img = Image.new("RGB", (W, H), (250, 250, 250))
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, 0, W - 1, H - 1], outline=RULE, width=SCALE)
    for i, line in enumerate(lines):
        dr.text((pad, pad + i * line_h), line, font=f, fill=FG)
    img.save(path)


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

BOX = set("┌┐└┘├┤┬┴┼─│")


# Emoji have no glyph in Liberation Sans, so PIL renders them as tofu boxes. The
# dev.to source uses medal emoji to rank rows, and rendering those tables to PNG
# turned the whole Rank column into empty squares -- visible only by looking at
# the output, which is why step one of shipping an image is opening it.
#
# Substitute rather than switch fonts: NotoColorEmoji is a CBDT bitmap face that
# PIL will only draw at one fixed size with embedded_color, and mixing faces
# inside a table cell to get three glyphs is not worth it.
#
# A medal ALONE is a rank, so it becomes its ordinal. A medal BESIDE something is
# a "this one won" marker, so it becomes a bullet the face actually has.
_MEDALS = {"\U0001F947": "1", "\U0001F948": "2", "\U0001F949": "3"}


def demoji(cell: str) -> str:
    text = cell.strip()
    if text and all(ch in _MEDALS or ch.isspace() for ch in text):
        return " ".join(_MEDALS[ch] for ch in text if ch in _MEDALS)
    for medal in _MEDALS:
        text = text.replace(medal, "\u25cf")
    return text.strip()


# MEDIUM HAS EXACTLY TWO HEADING SIZES. `#` and `##` both render as the big one;
# `###` and smaller both render as the small one. A 21-section article written
# with `##` therefore renders as 21 TITLES, which looks unhinged and is invisible
# until you view it on Medium.
#
# So every section heading is demoted to `####`, and the document's `#` title is
# DROPPED: Medium never fills its Title field from pasted content anyway, and the
# orphaned h1 just leaves a stray empty block at the top.
def demote_headings(lines: list[str]) -> list[str]:
    out, fenced = [], False
    for line in lines:
        if line.strip().startswith("```"):
            fenced = not fenced
            out.append(line)
            continue
        if not fenced and line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            text = line.lstrip("#").strip()
            if level == 1:
                continue          # title is a separate field; drop it
            out.append("#### " + text)
            continue
        out.append(line)
    return out


def convert(src: Path, outdir: Path, img_base: str = "", cover: Path | None = None) -> Path:
    text = src.read_text()

    # strip YAML front matter, keep title/description
    title, desc = src.stem, ""
    if text.startswith("---"):
        end = text.index("\n---", 3)
        fm, text = text[3:end], text[end + 4:]
        for line in fm.splitlines():
            if line.startswith("title:"):
                title = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("description:"):
                desc = line.split(":", 1)[1].strip().strip('"')

    slug = re.sub(r"[^a-z0-9]+", "-", src.stem.lower()).strip("-")
    imgdir = outdir / "img"
    imgdir.mkdir(parents=True, exist_ok=True)

    lines = demote_headings(text.split("\n"))
    out: list[str] = []
    n_tab = n_dia = 0
    i = 0
    while i < len(lines):
        line = lines[i]

        # fenced block?
        if line.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            block = lines[i + 1:j]
            if block and any(any(c in BOX for c in l) for l in block):
                n_dia += 1
                name = f"{slug}-diagram-{n_dia}.png"
                render_mono(block, imgdir / name)
                out += ["", f"![diagram](img/{name})", ""]
            else:
                out += lines[i:j + 1]
            i = j + 1
            continue

        # markdown table?
        if line.strip().startswith("|") and i + 1 < len(lines) and re.match(
            r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]
        ):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            hdr, body = parse_table(lines[i:j])
            hdr = [demoji(c) for c in hdr]
            body = [[demoji(c) for c in row] for row in body]
            n_tab += 1
            name = f"{slug}-table-{n_tab}.png"
            render_table(hdr, body, imgdir / name)
            out += ["", f"![table](img/{name})", ""]
            i = j
            continue

        out.append(line)
        i += 1

    md = "\n".join(out)
    tmp = outdir / f"{slug}.tmp.md"
    tmp.write_text(md)

    base = outdir / f"{slug}.tmp.html"
    subprocess.run(
        ["pandoc", "-f", "gfm", "-t", "html5", "--standalone",
         "--metadata", f"title={title}", "-o", str(base), str(tmp)],
        check=True,
    )
    tmp.unlink()

    h = base.read_text()
    base.unlink()

    # MEDIUM MAKES THE FIRST IMAGE IN THE BODY THE STORY COVER. Without this the
    # cover becomes whatever table happened to render first -- a screenshot of a
    # price table -- while the actual cover art, which only ever lived in dev.to
    # front matter, never reaches Medium at all. Nothing warns you.
    if cover and cover.exists():
        dst = outdir / "img" / cover.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if cover.resolve() != dst.resolve():
            dst.write_bytes(cover.read_bytes())
        h = h.replace("<body>", f'<body>\n<figure><img src="img/{cover.name}" '
                                f'alt="{html.escape(title)}" /></figure>', 1)

    # pandoc repeats the title in a header block; Medium supplies its own.
    h = h.replace('<header id="title-block-header">',
                  '<header id="title-block-header" hidden>')
    if desc:
        h = h.replace("</title>",
                      "</title>\n  <meta name=\"description\" content=\"%s\" />"
                      % html.escape(desc))
    # Preview styling only — Medium restyles everything on paste. This just
    # stops the local preview looking like a 1998 pandoc default.
    h = h.replace("</head>", """  <style>
    body{font-family:-apple-system,'Segoe UI',Roboto,'Liberation Sans',Arial,sans-serif;
         font-size:18px;line-height:1.58;max-width:42em;color:#242424;}
    h1,h2,h3,h4{font-weight:700;line-height:1.25;margin-top:1.8em;}
    h4{font-size:1.25em;}
    img{max-width:100%;height:auto;display:block;margin:1.6em 0;}
    pre{background:#f7f7f7;border:1px solid #e6e6e6;border-radius:4px;
        padding:12px 14px;overflow-x:auto;font-size:14px;line-height:1.45;}
    code{font-family:'Liberation Mono',Menlo,Consolas,monospace;}
    :not(pre)>code{background:#f2f2f2;padding:1px 5px;border-radius:3px;font-size:.9em;}
    blockquote{border-left:3px solid #ddd;margin-left:0;padding-left:1em;color:#555;}
    hr{border:0;border-top:1px solid #e6e6e6;margin:2.4em 0;}
  </style>
</head>""")

    # 1. self-contained: every local image inlined as a data: URI.
    #    Covers both the tables/diagrams we rendered into <outdir>/img and any
    #    image the article references itself (header art, screenshots), which
    #    resolve relative to the source .md.
    def inline(m: re.Match) -> str:
        ref = m.group(1)
        if ref.startswith(("http://", "https://", "data:")):
            return m.group(0)
        cand = (outdir / ref) if ref.startswith("img/") else (src.parent / ref)
        if not cand.exists():
            print(f"   ! missing image, left as-is: {ref}", file=sys.stderr)
            return m.group(0)
        mime = "image/png" if cand.suffix.lower() == ".png" else "image/jpeg"
        b64 = base64.b64encode(cand.read_bytes()).decode()
        return f'src="data:{mime};base64,{b64}"'

    embed = re.sub(r'src="([^"]+)"', inline, h)
    p_embed = outdir / f"{slug}-embed.html"
    p_embed.write_text(embed)

    # 2. hosted: absolute URLs for import-by-URL flows
    p_hosted = outdir / f"{slug}-hosted.html"
    p_hosted.write_text(h.replace('src="img/', f'src="{img_base}'))

    print(f"{src.name}: {n_tab} tables, {n_dia} diagrams")
    # The guidance printed here USED to say "paste the embed variant", and that
    # is wrong: Medium silently strips data: URI images on paste, so the embed
    # variant loses every image with no error and no placeholder.
    print(f"   USE THIS   -> {p_hosted}  (paste or import; needs medium/img committed AND pushed)")
    print(f"   not this   -> {p_embed}   ({p_embed.stat().st_size // 1024} KB; "
          f"data: URIs, Medium drops them all on paste)")
    print("   Medium never fills its Title field from pasted content -- set the title separately.")
    return p_embed


# The hosted variant's <img> URLs are DERIVED, never hardcoded, and this is the
# single most repeated mistake in this toolchain. A per-project copy of this
# script used to bake in its own project's path; a copy taken to a new project
# kept the old one, so every <img> in the hosted HTML pointed at another
# project's URLs -- all 404. The embed variant hides it completely, because its
# images are inlined, so the bug ships silently.
#
# Now that this script is CENTRAL rather than copied per project, deriving from
# the script's own location would be wrong too (it would resolve to "scripts").
# The only correct source is the ARTICLE's own directory.
#
# Override with --img-base=<url> whenever the images will not be served from
# <repo>/<article-dir>/medium/img/.
# DERIVED, never hardcoded. This constant used to be another project's repository,
# so every <img> in an article outside that project pointed at URLs that 404 --
# and the embed variant hid it completely, because its images are inlined. It is
# the most repeated bug in this toolchain, and it survived being written up in
# SKILL.md twice, because writing a hazard down does not remove it.
#
# The repository, branch and path are all knowable from the article's own
# location, so ask git rather than remember.
def default_img_base(src: Path) -> str:
    d = src.resolve().parent
    try:
        def g(*args):
            return subprocess.run(["git", "-C", str(d), *args],
                                  capture_output=True, text=True).stdout.strip()
        root, url = g("rev-parse", "--show-toplevel"), g("remote", "get-url", "origin")
        branch = g("symbolic-ref", "--short", "HEAD") or "main"
        if not root or not url:
            raise RuntimeError("not a git checkout with an origin remote")
        slug = re.sub(r"^git@github\.com:|^https://github\.com/", "", url)
        slug = re.sub(r"\.git$", "", slug)
        rel = d.relative_to(Path(root))
        return f"https://raw.githubusercontent.com/{slug}/{branch}/{rel}/medium/img/"
    except Exception as e:
        sys.exit(f"cannot derive --img-base from git ({e}). Pass --img-base "
                 f"explicitly: a wrong base 404s every image in the hosted "
                 f"variant, and the embed variant hides it.")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a.split("=")[0]: a.split("=", 1)[-1]
             for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        sys.exit(__doc__)
    src = Path(args[0])
    img_base = flags.get("--img-base") or default_img_base(src)
    outdir = Path(args[1]) if len(args) > 1 else Path("medium")
    cov = flags.get("--cover")
    cover = Path(cov) if cov else next(
        (c for c in sorted(src.parent.glob("*cover*.jpg")) + sorted(src.parent.glob("*cover*.png"))
         if "builder" not in c.name), None)
    convert(src, outdir, img_base, cover)
