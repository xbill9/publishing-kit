#!/usr/bin/env python3
r"""Render a LinkedIn post draft for an article, with links, and refuse to ship a broken one.

LinkedIn is the fourth destination and it is the one that takes NO markup. The
other three all render some. This script converts an article's front matter and
summary into a post the composer will show correctly, and fails on the four
things that go wrong silently.

WHY THIS IS A FILE AND NOT AN API CALL
--------------------------------------
LinkedIn's Posts API cannot create a draft. `lifecycleState` documents DRAFT as
"content that's accessible only to the author and is not yet published", and then
says PUBLISHED "is the only accepted field during creation" -- DRAFT is a state
you can read back, never one you can post into. So there is no equivalent of
dev.to's `published: false` here, and the safe artifact is a text file you paste
into the composer, which does have drafts. Anything that posts for you is
publishing, not drafting.
  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api

WHAT THE POST FIELD ACTUALLY SUPPORTS
-------------------------------------
Post text is the `commentary` field in LinkedIn's `little` format, whose entire
element set is: plain text, mentions, hashtags. No bold, no italics, no lists, no
link markup. A markdown `**bold**` or `[label](url)` reaches the reader as its own
punctuation.
  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/little-text-format

That page also carries the rule that costs an API poster a malformed post:

    "All reserved characters need to be escaped with a backslash, even if those
     characters are not used in one of the supported elements or templates."

Reserved: |  {  }  @  [  ]  (  )  <  >  #  \  *  _  ~

An article body is full of them. `--api` emits the escaped variant; the default
output is for the composer, which takes plain text and needs no escaping.

NO UNICODE PSEUDO-BOLD. The 𝗠𝗔𝗧𝗛𝗘𝗠𝗔𝗧𝗜𝗖𝗔𝗟 𝗕𝗢𝗟𝗗 trick is the usual workaround for
having no bold. A screen reader announces those code points one at a time or
skips them, so the headline of your post is the part that stops being readable.
This script refuses to emit them.

THE SHAPE OF THE POST IS A TEMPLATE, NOT CODE
---------------------------------------------
An announcement post is the same five moves every time, and writing them out again
per article is how they drift. `templates/linkedin-post.txt` holds the shape:

    {hook}          the first line, checked against the fold
    {description}   the article's own description, markdown stripped
    {bullets}       the article's Summary bullets, one per line
    {links}         one labelled link per destination

Wrap anything that should disappear when its value is empty in a block:

    [[bullets]]
    What is in it:

    {bullets}
    [[/bullets]]

An article with no Summary then drops the lead-in line with the bullets, instead
of stranding it above the links.

Swap that one file and every post changes shape. Nothing else here depends on it,
which is the same arrangement `references/house-style.md` has with the articles. A
missing template falls back to the built-in default, so the script still runs
standalone.

    make-linkedin.py <article>.md [--out FILE] [--links links.txt]
                     [--url key=URL ...] [--hook "..."] [--template FILE] [--api]

`links.txt` is `key = url`, one per line, `#` comments. A value of PENDING is
carried into the output as a visible placeholder AND fails the run, so a draft
with an unpublished link in it cannot be posted by accident.
"""

import argparse
import pathlib
import re
import sys

# LinkedIn's own docs give no number for the commentary limit -- only the error
# FIELD_LENGTH_TOO_LONG. 3,000 is the figure every third-party counter agrees on
# and it is NOT first-party. Treated as a hard stop because overshooting it is a
# rejected post either way.
MAX_CHARS = 3000

# Where the feed truncates with "...see more". Also third-party, and it moves with
# screen and font size: ~140 mobile, ~210 desktop. The hook is checked against the
# mobile figure and warned against the desktop one.
FOLD_MOBILE = 140
FOLD_DESKTOP = 210

# little's reserved set, first-party. Escaped for --api even outside an element.
RESERVED = "|{}@[]()<>#\\*_~"

# Two dev.to entries routed to two organizations are two different URLs. Labelling
# both of them "dev.to" ships a post with the same word against two links.
LABELS = {
    "devto-gde": "dev.to (Google Developer Experts)",
    "devto-aws": "dev.to (AWS Community Builders)",
    "builder": "AWS Builder Center",
    "medium": "Medium",
    "repo": "Source",
}

DEFAULT_TEMPLATE = ("{hook}\n\n{description}\n\n"
                    "[[bullets]]What is in it:\n\n{bullets}\n[[/bullets]]\n{links}\n")

FAILS, WARNS = [], []


def fail(m):
    FAILS.append(m)
    print(f"  FAIL  {m}")


def warn(m):
    WARNS.append(m)
    print(f"  WARN  {m}")


def ok(m):
    print(f"  ok    {m}")


def front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else ""


def field(fm, key):
    m = re.search(rf'^{key}:\s*"?(.*?)"?\s*$', fm, re.M)
    return m.group(1) if m else ""


def strip_markdown(s):
    """LinkedIn renders none of it, so anything left behind ships as punctuation."""
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)   # links keep their label
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"(?<!\w)[*_]([^*_]+)[*_](?!\w)", r"\1", s)
    s = s.replace("`", "")
    return re.sub(r"\s+", " ", s).strip()


def summary_bullets(text, n=4, section="Summary"):
    """The article's own bullets from one named section.

    Defaults to Summary, because a lifecycle write-up puts its conclusions
    there. An announcement has no Summary -- it ends in Links -- and its
    conclusions live under "What it does", so the section is a parameter rather
    than a constant. Hardcoding "Summary" produced a 468-character post from a
    9.5K article and warned about it instead of looking anywhere else.

    Source articles are hard-wrapped, so a bullet is its first line plus every
    indented continuation line under it. Taking only the first line truncates
    every bullet mid-sentence, which looks like prose and reads as a bug.
    """
    m = re.search(rf"^#+\s*{re.escape(section)}\s*$(.*?)(?=^#+\s|\Z)", text, re.S | re.M)
    if not m:
        return []
    out, buf = [], None
    for line in m.group(1).splitlines():
        b = re.match(r"^\s*[-*]\s+(.*)", line)
        if b:
            if buf is not None:
                out.append(buf)
            buf = b.group(1).strip()
        elif buf is not None and line.strip() and line.startswith((" ", "\t")):
            buf += " " + line.strip()
        elif buf is not None:
            out.append(buf)
            buf = None
    if buf is not None:
        out.append(buf)
    return [strip_markdown(b) for b in out[:n]]


def read_links(path, pairs):
    links = {}
    if path and pathlib.Path(path).exists():
        for ln in pathlib.Path(path).read_text().splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            k, _, v = ln.partition("=")
            links[k.strip()] = v.strip()
    for p in pairs:
        k, _, v = p.partition("=")
        links[k.strip()] = v.strip()
    return links


def escape_little(s):
    """Backslash-escape every reserved character, per the little spec."""
    return "".join("\\" + c if c in RESERVED else c for c in s)


def has_pseudo_bold(s):
    """Mathematical alphanumeric symbols read as gibberish to a screen reader."""
    return [c for c in s if 0x1D400 <= ord(c) <= 0x1D7FF]


def load_template(explicit):
    """The post shape lives in a file so it is written once, not once per article."""
    if explicit:
        return pathlib.Path(explicit).read_text()
    shipped = pathlib.Path(__file__).resolve().parent.parent / "templates" / "linkedin-post.txt"
    if shipped.exists():
        return shipped.read_text()
    return DEFAULT_TEMPLATE


def build(article, links, hook_override, template, section="Summary"):
    text = article.read_text()
    fm = front_matter(text)
    title = strip_markdown(field(fm, "title")) or article.stem
    desc = strip_markdown(field(fm, "description"))

    hook = hook_override or title
    bullets = summary_bullets(text, section=section)

    ordered = [k for k in ("devto-gde", "devto-aws", "builder", "medium", "repo") if k in links]
    # A key the ordering does not know is silently dropped from {links}, while the
    # resolver above still counts it as "resolved" -- so a typo like devto_gde for
    # devto-gde ships a post missing two of its four destinations and reports ok.
    unknown = [k for k in links if k not in ordered]
    if unknown:
        fail(f"link key(s) not in the render order, so they would be dropped: "
             f"{', '.join(sorted(unknown))}. Known keys: devto-gde, devto-aws, "
             f"builder, medium, repo.")

    values = {
        "hook": hook,
        "description": desc,
        "bullets": "\n".join(f"- {b}" for b in bullets),
        "links": "\n".join(f"{LABELS.get(k, k)}: {links[k]}" for k in ordered),
    }

    # [[key]] ... [[/key]] survives only if that value is non-empty. Without this a
    # missing Summary leaves the lead-in line stranded above the links, and the
    # script cannot special-case the wording -- the template owns the wording.
    def block(m):
        return m.group(2) if values.get(m.group(1), "").strip() else ""

    post = re.sub(r"\[\[(\w+)\]\](.*?)\[\[/\1\]\]\n?", block, template, flags=re.S)
    post = post.format(**values)
    post = re.sub(r"\n{3,}", "\n\n", post)
    return hook, post.strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--out")
    ap.add_argument("--links", default="links.txt")
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--hook")
    ap.add_argument("--template", help="post shape; defaults to templates/linkedin-post.txt")
    ap.add_argument("--bullets-from", default=None,
                    help="heading to take the post's bullets from (default: Summary, "
                         "or whatever linkedin.args beside the article says)")
    ap.add_argument("--no-write", action="store_true",
                    help="run the checks without touching the file. A pre-flight "
                        "must not mutate the artifact it is checking.")
    ap.add_argument("--api", action="store_true",
                    help="also write the little-escaped variant for the Posts API")
    a = ap.parse_args()

    src = pathlib.Path(a.article).resolve()

    # MEASURED: preflight.py regenerated this file with default flags and replaced
    # a 1,476-character post with a 468-character one, and the damaged version was
    # committed. Build flags have to outlive the command that first used them, so
    # they live beside the article.
    argsfile = src.parent / "linkedin.args"
    if a.bullets_from is None:
        a.bullets_from = "Summary"
        if argsfile.exists():
            for ln in argsfile.read_text().splitlines():
                ln = ln.strip()
                if ln.startswith("bullets-from"):
                    a.bullets_from = ln.split("=", 1)[1].strip()
    links = read_links(src.parent / a.links if not pathlib.Path(a.links).is_absolute()
                       else a.links, a.url)
    out = pathlib.Path(a.out) if a.out else src.parent / f"linkedin-{src.stem}.txt"

    print(f"\n{src.name} -> {out.name}")

    if not links:
        fail("no links: LinkedIn is the destination whose whole job is the link")
    hook, post = build(src, links, a.hook, load_template(a.template), a.bullets_from)
    if not summary_bullets(src.read_text(), section=a.bullets_from):
        warn(f"no bullets under '{a.bullets_from}'; the post carries the description "
             f"only. Try --bullets-from with a heading this article actually has.")

    # 1  LINKS RESOLVE -------------------------------------------------------
    pending = [k for k, v in links.items() if not v or v.upper() == "PENDING"]
    if pending:
        fail(f"{len(pending)} link(s) still PENDING: {', '.join(sorted(pending))}")
    else:
        ok(f"{len(links)} link(s) resolved")
    for k, v in links.items():
        if v and v.upper() != "PENDING" and not v.startswith("https://"):
            fail(f"{k} is not an https URL: {v}")

    # A dev.to draft URL carries a -temp-slug-<n> suffix that is replaced when the
    # article is published. Announcing one is announcing a link that will 404.
    temp = [k for k, v in links.items() if "temp-slug" in (v or "")]
    if temp:
        fail(f"{len(temp)} link(s) are unpublished draft URLs whose slug changes on "
             f"publish: {', '.join(sorted(temp))}")
    else:
        ok("no draft URLs; every slug is settled")

    # 2  THE FOLD ------------------------------------------------------------
    if len(hook) > FOLD_DESKTOP:
        fail(f"hook is {len(hook)} chars; truncated on desktop too (~{FOLD_DESKTOP})")
    elif len(hook) > FOLD_MOBILE:
        warn(f"hook is {len(hook)} chars; cut on mobile at ~{FOLD_MOBILE}")
    else:
        ok(f"hook fits the fold: {len(hook)} chars")

    # 3  LENGTH --------------------------------------------------------------
    if len(post) > MAX_CHARS:
        fail(f"post is {len(post)} chars, over the {MAX_CHARS} limit")
    else:
        ok(f"post is {len(post)} chars of {MAX_CHARS}")

    # 4  NO MARKUP SURVIVES --------------------------------------------------
    leftovers = [m for m in ("**", "](", "`", "##") if m in post]
    if leftovers:
        fail(f"markdown left in the post, which LinkedIn renders literally: {leftovers}")
    else:
        ok("no markdown left; LinkedIn renders none of it")

    # an unclosed or misspelled block marker otherwise ships as visible scaffolding
    if "[[" in post or "]]" in post:
        fail("template block markers left in the post; check [[key]] ... [[/key]] pairing")
    else:
        ok("no template scaffolding left")

    # 5  ACCESSIBILITY -------------------------------------------------------
    pb = has_pseudo_bold(post)
    if pb:
        fail(f"{len(pb)} Unicode pseudo-bold character(s); screen readers cannot read them")
    else:
        ok("no Unicode pseudo-bold")

    if a.no_write:
        ok(f"checked without writing ({out.name} left alone)")
    else:
        out.write_text(post)
    if a.api and not a.no_write:
        api_out = out.with_suffix(".little.txt")
        api_out.write_text(escape_little(post))
        ok(f"little-escaped variant for the Posts API -> {api_out.name}")

    print(f"\n--- above the fold ({FOLD_MOBILE} chars) ---\n{post[:FOLD_MOBILE]}")
    print(f"\n{len(FAILS)} fail, {len(WARNS)} warn")
    if FAILS:
        print("\nThe file was written so you can read it. It is not postable.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
