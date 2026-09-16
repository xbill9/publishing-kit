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

A third state, added 2026-09-16: a claim may be MEASURED EARLIER AND DELIBERATELY
NOT RE-RUN. Until now that was indistinguishable from memory, so this kit's own
article failed on a claim its ledger already labelled `LOG -- carried from the
kit's log with the date it was taken, and NOT re-measured here`. A check that can
never go green stops being read, and the untraced claim beside it went unfixed for
a week. So rows under a `## LOG` heading in the article's ledger (`CLAIMS.md` next
to it, or --ledger) cite a claim instead of proving it. Two guards, because this is
a hole by design:

  * the row must carry a date, and the claim must appear in it LITERALLY -- not
    by the digit-normalised match the evidence files get, which "2026-08-30" alone
    would satisfy for half the counts in an article;
  * the ledger may not live inside --evidence. It restates every number, so a
    ledger inside the evidence set traces everything by construction. That is not
    hypothetical: this article's ledger was first written into `evidence/` and
    scored a perfect run.

LOG citations are printed, counted separately, and do not fail the run. They are a
claim about provenance, so they are only ever as good as the ledger.
"""

import argparse
import json
import pathlib
import re
import sys

# Claims worth tracing. Ordinary prose numbers ("three reasons", "two platforms")
# are excluded by the shape of these patterns rather than by a stop-list.
#
# Each pattern carries an example it must match: the positive control. main()
# refuses to run if any pattern misses its own example, because a zero from a
# pattern that cannot fire is not a result.
PATTERNS = [
    (r"\$\s?\d[\d,]*\.?\d*", "price", "$0.42"),
    (r"\b\d[\d,]*\.\d+\s*(?:tok/s|tokens/s|GB/s|GiB/s|MB/s|ms|s\b|%)", "measurement",
     "73.75 tok/s"),
    (r"\b\d[\d,]{2,}\s*(?:tokens?|MiB|GiB|GB|MB|bytes|B)\b", "quantity", "15,360 MiB"),
    (r"\bv?\d+\.\d+\.\d+(?:rc\d+)?(?:\.dev\d+)?\b", "version", "v0.26.0"),
    (r"\b(?:ami|i|subnet|sg|vol|snap)-[0-9a-f]{8,}\b", "cloud-id", "ami-0abc1234def56789"),
    (r"\bsha256:[0-9a-f]{8,}\b", "digest", "sha256:6d805f0f"),
    (r"\bsm_\d{2,3}\b|\bSM \d\.\d\b", "arch", "sm_75"),
    (r"\b\d[\d,]*\s*(?:vCPUs?|chips?|GPUs?)\b", "capacity", "8 vCPUs"),
    # Ratios are the shape most often carried in from memory, and until
    # 2026-09-07 nothing here matched one: a headline "4.46x" went unextracted
    # while the run reported "0 untraced" over four latency readings. A ratio is
    # almost always arithmetic, so tracing it means recording the derivation.
    (r"\b\d[\d,]*(?:\.\d+)?x\b", "ratio", "4.46x"),
    # Until 2026-09-10 none of these four matched, and this kit's own article --
    # whose headline facts are "47 of 62", "1376x768", "95px" and "2.381:1" --
    # reported "0 claim(s), 0 untraced".
    (r"\b\d+(?:\.\d+)?:1\b", "ratio", "2.381:1"),
    (r"\b\d+ of \d+\b", "count", "47 of 62"),
    (r"\b\d{2,5}x\d{2,5}\b", "dimensions", "1376x768"),
    (r"\b\d+(?:\.\d+)?\s?px\b", "pixels", "95px"),
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


DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def load_ledger(path):
    """Dated rows under the ledger's `## LOG` heading, as (row, date).

    Only that section. The ledger's other tables restate numbers that ARE
    supposed to trace to an artifact, and letting those cite themselves is the
    by-construction failure this tool exists to avoid.
    """
    rows = []
    if not path or not path.exists():
        return rows
    section = False
    for ln in path.read_text().splitlines():
        if ln.startswith("## "):
            section = re.match(r"##\s+LOG\b", ln) is not None
            continue
        if not section or not ln.strip().startswith("|"):
            continue
        d = DATE.search(ln)
        if d:
            rows.append((ln, d.group(0)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--evidence", nargs="*", default=[])
    ap.add_argument("--exempt", action="append", default=[])
    ap.add_argument("--ledger", default=None,
                    help="claim ledger whose `## LOG` rows may cite a dated, "
                         "not-re-measured claim; default <article dir>/CLAIMS.md")
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

    broken = [(kind, ex) for pat, kind, ex in PATTERNS if not re.search(pat, ex)]
    if broken:
        for kind, ex in broken:
            print(f"  FAIL  {kind} pattern does not match its own control {ex!r}")
        print("\nA pattern that cannot match its control cannot report a claim. Fix it.")
        return 1

    claims = {}
    for pat, kind, _ in PATTERNS:
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

    ledger = pathlib.Path(a.ledger) if a.ledger else src.parent / "CLAIMS.md"
    if a.ledger and not ledger.exists():
        print(f"  FAIL  ledger does not exist: {ledger}")
        return 1
    log_rows = load_ledger(ledger)

    missing = [e for e in a.evidence if not pathlib.Path(e).exists()]
    blobs = load_evidence(a.evidence)
    print(f"{src.name}: {len(claims)} claim(s) against {len(blobs)} evidence file(s)"
          + (f", {len(log_rows)} dated log row(s)" if log_rows else "") + "\n")

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

    # The trap this kit already fell into, and which a first version of the guard
    # below did NOT catch: a ledger inside --evidence restates every number, so
    # every claim traces to it and the run is green by construction. Checking the
    # --ledger path is not enough -- the ledger arrives as an ordinary evidence
    # blob whatever it is called. Detect it by shape, in the files actually read.
    ledgers = [f for f, raw, _ in blobs
               if f.name == "CLAIMS.md" or re.search(r"^##\s+LOG\b", raw, re.M)]
    if ledgers:
        for f in ledgers:
            print(f"  FAIL  a claim ledger is inside the evidence set: {f}")
        print("\nA ledger restates the numbers, so every claim would trace to it by "
              "construction. Keep it beside the article and name it with --ledger, "
              "outside --evidence.")
        return 1

    unverified, cited = [], []
    for c, kind in sorted(claims.items()):
        n = norm(c)
        hit = None
        for f, raw, flat in blobs:
            if c in raw or (n and len(n) >= 3 and n in norm(flat)):
                hit = f.name
                break
        if hit:
            print(f"  ok    {kind:12s} {c:28s} <- {hit}")
            continue
        # Literal match only: the digit-normalised one would let a row's own
        # date stand in for the claim it is supposed to be citing.
        row = next((r for r in log_rows if c in r[0]), None)
        if row:
            print(f"  LOG   {kind:12s} {c:28s} <- {ledger.name} {row[1]}, not re-measured")
            cited.append((kind, c))
        else:
            print(f"  TRACE {kind:12s} {c:28s} <- nothing")
            unverified.append((kind, c))

    traced = len(claims) - len(unverified) - len(cited)
    print(f"\n{traced} traced, {len(cited)} cited from the log, {len(unverified)} untraced")
    if cited:
        print("\nA log citation is a claim about provenance, not a measurement. It "
              "says the number was taken on that date and deliberately not re-run, "
              "and it is worth exactly as much as the ledger it came from.")
    if unverified:
        print("\nEach untraced claim is either: measured but the artifact was not "
              "supplied, arithmetic (label it as such in the text), or asserted "
              "from memory -- which is the one to fix.")
    return 1 if unverified and not a.warn_only else 0


if __name__ == "__main__":
    sys.exit(main())
