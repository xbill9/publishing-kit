#!/usr/bin/env python3
"""Derive the AWS Builder Center article from the dev.to source, by subtraction.

The Builder Center version is the dev.to one minus what Builder Center does not
take, plus what it requires. That is a transformation, not a document, and it was
a snippet retyped by hand eight times in one session before it became this file --
during which the two copies drifted twice.

    make-builder.py <devto-article>.md --out builder-<slug>.md \\
        --title "..." --subtitle "..."

What it removes, and why each one:

  YAML front matter   Title and Description are separate editor fields there.
  emoji               Not in the house style for Builder Center.
  the emoji table row Once the medals are gone that row compares nothing.

What it adds:

  # Title            } stripped again by serve-body.py, because they are
  *Subtitle: ...*    } separate fields -- kept here so the file is self-contained
  the AWS disclaimer  Required: "Any opinions in this article are those of the
                      individual author and may not reflect the opinions of AWS."

Tables are checked against Builder Center's practical width. MEASURED: seven
columns get squeezed until cells break mid-token, so more than five warns.
"""

import argparse
import pathlib
import re
import sys

DISCLAIMER = ("Any opinions in this article are those of the individual author "
              "and may not reflect the opinions of AWS.")

# Builder Center's house style takes NO emoji. This used to be a list of the ones
# the author's style happened to use -- medals and status markers -- which is an
# allow-list pretending to be a filter: the moment an article used 🐕🍖 they went
# straight through and landed in the published draft. Match the ranges instead.
EMOJI_RE = re.compile(
    "[" 
    "\U0001F300-\U0001FAFF"   # symbols, pictographs, emoticons, supplemental
    "\U00002600-\U000027BF"   # misc symbols and dingbats
    "\U0001F1E6-\U0001F1FF"   # regional indicators
    "\U00002190-\U000021FF"   # arrows that render as emoji on some platforms
    "\uFE0F\u20E3"            # variation selector, combining keycap
    "]+", flags=re.UNICODE)

MAX_COLS = 5


def strip_front_matter(text):
    return re.sub(r"\A---\n.*?\n---\n\n?", "", text, flags=re.S)


def widest_table(text):
    widest, fenced = 0, False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
        if not fenced and line.strip().startswith("|"):
            widest = max(widest, line.count("|") - 1)
    return widest


def convert(src_text, title, subtitle):
    body = strip_front_matter(src_text)
    body = EMOJI_RE.sub("", body)
    body = re.sub(r"[ \t]+$", "", body, flags=re.M)   # trailing space where one was
    # a row that only ever compared emoji support compares nothing without them
    body = re.sub(r"^\| Emoji \|.*\n", "", body, flags=re.M)
    head = f"# {title}\n\n"
    if subtitle:
        head += f"*Subtitle: {subtitle}*\n\n"
    return head + body.rstrip("\n") + "\n\n" + DISCLAIMER + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default="")
    a = ap.parse_args()

    src = pathlib.Path(a.source)
    out = pathlib.Path(a.out)
    text = convert(src.read_text(), a.title, a.subtitle)
    out.write_text(text)

    left = EMOJI_RE.findall(text)
    cols = widest_table(text)
    print(f"{src.name} -> {out.name}  {len(text):,} chars, {len(text.splitlines())} lines")
    fails = 0
    if left:
        print(f"  FAIL  emoji survived the strip: {sorted(set(left))}")
        fails += 1
    else:
        print("  ok    no emoji")
    if cols > MAX_COLS:
        print(f"  FAIL  widest table is {cols} columns; Builder Center squeezes "
              f"past {MAX_COLS} until cells break mid-token")
        fails += 1
    else:
        print(f"  ok    widest table is {cols} columns")
    if DISCLAIMER in text:
        print("  ok    AWS disclaimer present")
    else:
        print("  FAIL  AWS disclaimer missing")
        fails += 1
    if text.startswith("# "):
        print("  ok    title and subtitle carried as strippable lines")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
