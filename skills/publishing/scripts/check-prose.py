#!/usr/bin/env python3
"""Fail an article whose prose uses phrasing the author has banned.

    check-prose.py <article>.md [--style references/house-style.md]

The author corrected the same prose habits in four sessions running: narrating
the work instead of reporting it ("an earlier draft claimed", "the first version
of the driver", "those runs were discarded"), rhetorical contrast and reveal
lines ("This is not a language verdict.", "a different request, not a slower
client", "It is not the one with the bigger ratio."), filler that signals
sincerity ("honest", "actually", "until it didn't"), and internal jargon a
reader outside the repo cannot parse ("the control", "probe", "separable",
"p50"). Each correction held for one article. A rule that has to be remembered
is a rule that gets half-applied, so this one is a check that exits non-zero.

The patterns are not in this file. They live in a ```prose-lint``` block in
references/house-style.md, because house-style.md is the kit's one retargeting
seam: another author swaps that file and gets their own list. Each line is

    SEVERITY | CATEGORY | regex | what to write instead

SEVERITY is FAIL or WARN. Regexes are case-insensitive and run over prose only:
front matter title and description, headings, paragraphs, list items and table
cells. Fenced and indented code, inline `code` and URLs are removed first, so
command output that happens to print "probes" or "p50" is never flagged.
"""

import argparse
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_STYLE = HERE.parent / "references" / "house-style.md"


def load_rules(style_path):
    text = style_path.read_text()
    m = re.search(r"```prose-lint\n(.*?)```", text, re.S)
    if not m:
        sys.exit(f"{style_path}: no ```prose-lint``` block; nothing to check against")
    rules = []
    for n, line in enumerate(m.group(1).splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(" | ")]
        if len(parts) != 4 or parts[0] not in ("FAIL", "WARN"):
            sys.exit(f"{style_path}: prose-lint line {n} is not "
                     f"'SEVERITY | CATEGORY | regex | advice': {line!r}")
        try:
            rx = re.compile(parts[2], re.I)
        except re.error as e:
            sys.exit(f"{style_path}: prose-lint line {n}: bad regex: {e}")
        rules.append((parts[0], parts[1], rx, parts[3]))
    return rules


def prose_lines(article_text):
    """(line number, prose text) for every line a reader reads as prose."""
    lines = article_text.splitlines()
    out = []
    i = 0
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            key, _, val = lines[i].partition(":")
            if key.strip() in ("title", "description"):
                out.append((i + 1, val.strip().strip('"')))
            i += 1
        i += 1
    fenced = False
    for n in range(i, len(lines)):
        line = lines[n]
        # A reference list quotes other people's titles verbatim.
        if re.match(r"#+\s*references\s*$", line.strip(), re.I):
            break
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced or line.startswith("    ") or line.startswith("\t"):
            continue
        line = re.sub(r"`[^`]*`", " ", line)
        line = re.sub(r"\]\([^)]*\)", "]", line)
        line = re.sub(r"https?://\S+", " ", line)
        if line.strip():
            out.append((n + 1, line))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--style", default=str(DEFAULT_STYLE))
    a = ap.parse_args()

    rules = load_rules(pathlib.Path(a.style))
    article = pathlib.Path(a.article)
    fails = warns = 0
    for n, text in prose_lines(article.read_text()):
        for sev, cat, rx, advice in rules:
            for m in rx.finditer(text):
                hit = m.group(0).strip()
                print(f"  {sev:<5} {cat:<10} line {n}: {hit!r}  -> {advice}")
                if sev == "FAIL":
                    fails += 1
                else:
                    warns += 1
    print(f"\n{article.name}: {len(rules)} rule(s), {fails} fail, {warns} warn")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
