#!/usr/bin/env python3
"""Trace every factual claim in an article back to an artifact.

An article is a set of assertions. This extracts the ones a reader could check --
measurements, prices, versions, cloud identifiers -- and tells you which of them
appear in NO evidence file you supplied.

It cannot tell you a number is true. It tells you which numbers you are asserting
on memory, which is where wrong numbers come from. Prose is not evidence: a figure
that survives only in another article, a comment, or a chat log has no artifact
behind it and should not be restated.

    check-facts.py article.md --evidence run.json results.csv notes.md
    check-facts.py article.md --evidence bench/ --exempt 2026 --exempt 1.5

Exit codes: 0 all traced, 1 something unverified.

Whitelist deliberate exceptions with --exempt (repeatable, substring match), and
put standing ones in a `.factsignore` next to the article, one per line.
"""

import argparse
import json
import pathlib
import re
import sys

# Claims worth tracing. Ordinary prose numbers ("three reasons", "two platforms")
# are excluded by the shape of these patterns rather than by a stop-list.
PATTERNS = [
    (r"\$\s?\d[\d,]*\.?\d*", "price"),
    (r"\b\d[\d,]*\.\d+\s*(?:tok/s|tokens/s|GB/s|GiB/s|MB/s|ms|s\b|%)", "measurement"),
    (r"\b\d[\d,]{2,}\s*(?:tokens?|MiB|GiB|GB|MB|bytes|B)\b", "quantity"),
    (r"\bv?\d+\.\d+\.\d+(?:rc\d+)?(?:\.dev\d+)?\b", "version"),
    (r"\b(?:ami|i|subnet|sg|vol|snap)-[0-9a-f]{8,}\b", "cloud-id"),
    (r"\bsha256:[0-9a-f]{8,}\b", "digest"),
    (r"\bsm_\d{2,3}\b|\bSM \d\.\d\b", "arch"),
    (r"\b\d[\d,]*\s*(?:vCPUs?|chips?|GPUs?)\b", "capacity"),
]

NUM = re.compile(r"[\d.]+")


def norm(s):
    """Compare on digits alone: '15,360 MiB' and '15360' are the same claim."""
    return "".join(NUM.findall(s.replace(",", "")))


def load_evidence(paths):
    blobs = []
    for p in paths:
        p = pathlib.Path(p)
        files = sorted(p.rglob("*")) if p.is_dir() else [p]
        for f in files:
            if not f.is_file():
                continue
            try:
                t = f.read_text(errors="ignore")
            except Exception:
                continue
            if f.suffix == ".json":
                try:  # flatten so nested numbers are searchable as text
                    t += "\n" + json.dumps(json.loads(t))
                except Exception:
                    pass
            blobs.append((f, t, t.replace(",", "")))
    return blobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--evidence", nargs="*", default=[])
    ap.add_argument("--exempt", action="append", default=[])
    ap.add_argument("--warn-only", action="store_true")
    a = ap.parse_args()

    src = pathlib.Path(a.article)
    text = src.read_text()

    # strip fenced code: it is usually pasted tool output, i.e. evidence itself
    prose = re.sub(r"```.*?```", "", text, flags=re.S)

    exempt = list(a.exempt)
    ig = src.parent / ".factsignore"
    if ig.exists():
        exempt += [ln.strip() for ln in ig.read_text().splitlines()
                   if ln.strip() and not ln.startswith("#")]

    claims = {}
    for pat, kind in PATTERNS:
        for m in re.finditer(pat, prose):
            c = re.sub(r'\s+', ' ', m.group(0)).strip()
            if any(e in c for e in exempt):
                continue
            claims.setdefault(c, kind)

    if not a.evidence:
        print("no --evidence given; listing claims that need artifacts\n")
        for c, k in sorted(claims.items()):
            print(f"  {k:12s} {c}")
        print(f"\n{len(claims)} claim(s) to trace")
        return 0

    missing = [e for e in a.evidence if not pathlib.Path(e).exists()]
    blobs = load_evidence(a.evidence)
    print(f"{src.name}: {len(claims)} claim(s) against {len(blobs)} evidence file(s)\n")

    # A green run against an evidence path that is not there is the worst result
    # this tool can produce: it reads as "every number traces" when nothing was
    # read at all. A typo'd or cwd-relative path did exactly that.
    if missing:
        for e in missing:
            print(f"  FAIL  evidence path does not exist: {e}")
        print("\nNothing was read, so nothing was checked. Fix the path.")
        return 1
    if not blobs:
        print("  FAIL  evidence path(s) contain no readable files")
        print("\nNothing was read, so nothing was checked.")
        return 1

    unverified = []
    for c, kind in sorted(claims.items()):
        n = norm(c)
        hit = None
        for f, raw, flat in blobs:
            if c in raw or (n and len(n) >= 3 and n in norm(flat)):
                hit = f.name
                break
        if hit:
            print(f"  ok    {kind:12s} {c:28s} <- {hit}")
        else:
            print(f"  TRACE {kind:12s} {c:28s} <- nothing")
            unverified.append((kind, c))

    print(f"\n{len(claims) - len(unverified)} traced, {len(unverified)} untraced")
    if unverified:
        print("\nEach untraced claim is either: measured but the artifact was not "
              "supplied, arithmetic (label it as such in the text), or asserted "
              "from memory -- which is the one to fix.")
    return 1 if unverified and not a.warn_only else 0


if __name__ == "__main__":
    sys.exit(main())
