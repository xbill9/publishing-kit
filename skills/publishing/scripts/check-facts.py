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
    by the number match the evidence files get, which "2026-08-30" alone
    would satisfy for half the counts in an article;
  * the ledger may not live inside --evidence. It restates every number, so a
    ledger inside the evidence set traces everything by construction. That is not
    hypothetical: this article's ledger was first written into `evidence/` and
    scored a perfect run.

LOG citations are printed, counted separately, and do not fail the run. They are a
claim about provenance, so they are only ever as good as the ledger.

A fifth state, added 2026-11-15: DISPUTED. An audit of a paper (research-kit's
math-sandbox, ablation-stat-auditor) writes JSON records that carry the paper's
number AND a verdict on it:

    {"statement": ..., "paper_value": 4.2e-09, "computed": 7.1786e-09,
     "verdict": "MISMATCH", "reason": ...}

Fed as --evidence, such a file used to trace the paper's wrong number, because the
number is in it. Now a claim equal to the paper_value of a MISMATCH or NOT
CHECKABLE record fails as DISPUTED, whichever other file it also appears in. For a
MISMATCH whose paper_value and computed hold the same count of numbers, only the
numbers that disagree at the paper's own precision are disputed (39.5% is right
in "39.5% [31.5, 48.1]"; 48.1 is not). A disputed claim the article states on
purpose, with its caveat, is acknowledged by a row under `## DISPUTED` in the
ledger that contains the claim literally.
"""

import argparse
import json
import pathlib
import re
import sys

from bodytext import strip_fenced

SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
_W = "|".join(sorted(WORDS, key=len, reverse=True))
# Mantissa, then one of: e-09 | × 10⁻⁹ | x 10^-9 / *10**-9 | "times ten to the minus nine".
# The exponent must be marked (superscript, ^ or **): a bare "1920×1080" or
# "1920x1080" is a dimension, and an unmarked form read it as 1920 × 10^80.
SCI_PAT = (r"(?<![\w.])\d+(?:\.\d+)?(?:[eE][-+]?\d+(?!\w|\.\d)"
           r"|\s?[×x*·]\s?10(?:\s?(?:\^|\*\*)\s?[-+−]?\d+|[⁻⁺]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)"
           r"|\s(?:times|x) ten to the (?:power of )?(?:minus |negative |plus )?(?:" + _W + r"|\d+)\b)")
SCI = re.compile(SCI_PAT)


def sci_token(m):
    """Canonical text for a scientific-notation number: 4.2e-09, 4.2 × 10⁻⁹ -> 4.2e-9."""
    t = m.group(0)
    mant = re.match(r"\d+(?:\.\d+)?", t).group(0)
    rest = t[len(mant):].translate(SUP).replace("−", "-")
    w = re.search(r"(minus |negative )?(" + _W + r"|\d+)$", rest)
    if w and re.search(r"ten to the", rest):
        exp = WORDS.get(w.group(2), None)
        exp = int(w.group(2)) if exp is None else exp
        exp = -exp if w.group(1) else exp
    else:
        exp = int(re.search(r"[-+]?\d+$", rest.replace("**", "^")).group(0))
    return f"{mant}e{exp}"


# Claims worth tracing. Ordinary prose numbers ("three reasons", "two platforms")
# are excluded by the shape of these patterns rather than by a stop-list.
#
# Each pattern carries an example it must match: the positive control. main()
# refuses to run if any pattern misses its own example, because a zero from a
# pattern that cannot fire is not a result.
PATTERNS = [
    (r"\$\s?\d+(?:,\d{3})*(?:\.\d+)?", "price", "$0.42"),
    (r"\b\d[\d,]*\.\d+\s*(?:tok/s|tokens/s|GB/s|GiB/s|MB/s|ms|s\b|%|bits?\b)", "measurement",
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
    # Until 2026-11-15 no pattern matched scientific notation, so a narration
    # stating "Fisher p = 4.2e-9" twice -- the most disputed number in the paper
    # it described -- was never extracted as a claim.
    (SCI_PAT, "scientific", "4.2e-9"),
    (SCI_PAT, "scientific", "4.2 × 10⁻⁹"),
    (SCI_PAT, "scientific", "4.2 times ten to the minus nine"),
    (r"\bp\s?[=<]\s?0?\.\d+\b(?!\s?(?:[eE]|[×x*]\s?10|times))", "p-value", "p = 0.0141"),
]

# Claims and evidence compare as NUMBERS, not as a stream of digits. MEASURED
# 2026-10-31: every number in a file used to be concatenated, so "12 then 3.4"
# became "123.4" and traced a claim of 123.4 ms, and "rows 147 and 629" traced
# "47 of 62". A number now matches a whole number, and a multi-number claim needs
# its numbers adjacent, in order. That also retires `4.35 s` matching `4.355`.
NUM = re.compile(r"(?<![\d.,])\d{1,3}(?:,\d{3})+(?:\.\d+)*|(?<![\d.,])\d+(?:\.\d+)*")
LITERAL_ONLY = ("cloud-id", "digest")     # hex: digits inside them mean nothing


def numbers(s):
    """Whole numbers in order; a scientific-notation number is ONE number."""
    out, last = [], 0
    for m in SCI.finditer(s):
        out += [n.replace(",", "") for n in NUM.findall(s[last:m.start()])]
        out.append(sci_token(m))
        last = m.end()
    return out + [n.replace(",", "") for n in NUM.findall(s[last:])]


def key(nums):
    return "\0" + "\0".join(nums) + "\0"


def load_evidence(paths):
    blobs = []
    for p in paths:
        p = pathlib.Path(p)
        files = sorted(p.rglob("*")) if p.is_dir() else [p]
        for f in files:
            if not f.is_file():
                continue
            # Strict decode. errors="ignore" turned PNGs and compressed traces
            # into random digits that matched claims by coincidence.
            try:
                t = f.read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            disputed = []
            if f.suffix == ".json":
                try:  # flatten so nested numbers are searchable as text
                    doc = json.loads(t)
                    t += "\n" + json.dumps(doc)
                    disputed = disputed_numbers(doc)
                except Exception:
                    pass
            blobs.append((f, t, key(numbers(t)), disputed))
    return blobs


# research-kit audit records: a JSON object with "paper_value" and "verdict".
DISPUTED_VERDICTS = ("MISMATCH", "NOT CHECKABLE")


def _flat(v):
    if isinstance(v, bool) or v is None:
        return []
    if isinstance(v, (int, float)):
        return [v]
    if isinstance(v, dict):
        return [x for y in v.values() for x in _flat(y)]
    if isinstance(v, list):
        return [x for y in v for x in _flat(y)]
    return []


def _agrees(paper, computed):
    """Does `computed` round to `paper` at the precision the paper printed it?"""
    tok = numbers(json.dumps(paper))[0]
    if "e" in tok:  # significant figures of the mantissa
        mant = tok.split("e")[0]
        sig = len(mant.replace(".", "").lstrip("0")) or 1
        return float(f"{computed:.{sig - 1}e}") == float(f"{paper:.{sig - 1}e}")
    dec = len(tok.split(".")[1]) if "." in tok else 0
    return round(computed, dec) == round(paper, dec)


def disputed_numbers(doc):
    """One entry per audit record that disputes something: (the record's paper
    numbers in order, the positions among them that are disputed, verdict, label,
    statement).

    A claim is matched against a record as a whole sequence, the way it is traced
    against evidence. MEASURED 2026-11-16 on five outputs audited by research-kit
    (this kit's walk-through as published and as corrected, the studio page, the
    comic, and the write-up of that run): matching any one number of a claim to
    any one disputed number raised 34 flags, and 22 were about something else --
    `2.381:1` against a record of exit status 1, `4px` against code-block line
    counts [2, 2, 1, 4], `95px` against "95 columns". Matched as a sequence, with
    the unit rule below and the stylesheet stripped, 12 remain, every one a real
    dispute (the Medium 0 of 4 / 4 of 4, the 320px card width).
    """
    out = []

    def walk(x):
        if isinstance(x, list):
            for y in x:
                walk(y)
        if not isinstance(x, dict):
            return
        v = str(x.get("verdict", "")).strip().upper()
        if "paper_value" in x and v in DISPUTED_VERDICTS:
            paper, comp = _flat(x["paper_value"]), _flat(x.get("computed"))
            label = str(x.get("id") or x.get("statement") or "")[:60]
            pairs = len(paper) == len(comp) and v == "MISMATCH"
            toks = [numbers(json.dumps(pv))[0] for pv in paper]
            bad = {i for i, pv in enumerate(paper) if not (pairs and _agrees(pv, comp[i]))}
            if bad:
                out.append((toks, bad, v, label, str(x.get("statement") or "")))
        for y in x.values():
            walk(y)

    walk(doc)
    return out


UNIT_WORDS = {"px": r"px|pixels?"}


def disputes_claim(rec, claim, nums):
    """Does audit record `rec` dispute `claim`, whose numbers are `nums`?

    The claim's numbers must sit together, in order, in the record's paper value,
    covering at least one disputed position. A single number with a word unit
    (`95px`, `15 KB`) must also appear with that unit in the record's statement
    when the record has one: a record about "95 columns" or "exits 1" is about
    something else.
    """
    toks, bad, _, _, statement = rec
    k = len(nums)
    if not k or not any(toks[i:i + k] == nums and bad & set(range(i, i + k))
                        for i in range(len(toks) - k + 1)):
        return False
    unit = re.search(r"\d\s?([A-Za-z]+)$", claim)
    if k == 1 and unit and statement:
        u = UNIT_WORDS.get(unit.group(1).lower(), re.escape(unit.group(1)))
        return re.search(rf"(?<![\d.]){re.escape(nums[0])}\s?(?:{u})\b", statement, re.I) is not None
    return True


# An HTML page's stylesheet is full of lengths (1px, 6px) no reader sees.
STYLE = re.compile(r"<style\b.*?</style>|\sstyle=(\"[^\"]*\"|'[^']*')", re.S | re.I)


DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def load_ledger(path, heading="LOG"):
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
            section = re.match(rf"##\s+{heading}\b", ln) is not None
            continue
        if not section or not ln.strip().startswith("|"):
            continue
        d = DATE.search(ln)
        if d or heading != "LOG":
            rows.append((ln, d.group(0) if d else ""))
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
    prose = strip_fenced(text)
    if src.suffix.lower() in (".html", ".htm"):
        prose = STYLE.sub(" ", prose)

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
    noted_rows = load_ledger(ledger, "DISPUTED")

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
    ledgers = [f for f, raw, _, _ in blobs
               if f.name == "CLAIMS.md" or re.search(r"^##\s+(?:LOG|DISPUTED)\b", raw, re.M)]
    if ledgers:
        for f in ledgers:
            print(f"  FAIL  a claim ledger is inside the evidence set: {f}")
        print("\nA ledger restates the numbers, so every claim would trace to it by "
              "construction. Keep it beside the article and name it with --ledger, "
              "outside --evidence.")
        return 1

    disputes = [(rec, f.name) for f, _, _, ds in blobs for rec in ds]

    unverified, cited, disputed, noted = [], [], [], []
    for c, kind in sorted(claims.items()):
        nums = numbers(c)
        # A verdict outranks a match: the paper's wrong number is in the audit
        # file (as the paper's claim) and usually in the paper too, so it would
        # always trace. Checked first, on whole numbers, for every claim kind.
        d = None if kind in LITERAL_ONLY else next(
            ((rec[2], rec[3], fname) for rec, fname in disputes if disputes_claim(rec, c, nums)), None)
        if d:
            row = next((r for r in noted_rows if c in r[0]), None)
            if row:
                print(f"  NOTED {kind:12s} {c:28s} <- {d[0]} in {d[2]}, caveat in {ledger.name}")
                noted.append((kind, c))
            else:
                print(f"  DISPUTED {kind:9s} {c:28s} <- {d[0]} in {d[2]} ({d[1]})")
                disputed.append((kind, c))
            continue
        n = key(nums) if kind not in LITERAL_ONLY and len("".join(nums)) >= 3 else None
        hit = None
        for f, raw, stream, _ in blobs:
            if c in raw or (n and n in stream):
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

    traced = len(claims) - len(unverified) - len(cited) - len(disputed) - len(noted)
    print(f"\n{traced} traced, {len(cited)} cited from the log, {len(unverified)} untraced"
          + (f", {len(disputed)} disputed" if disputed or disputes else "")
          + (f", {len(noted)} disputed with a caveat" if noted else ""))
    if cited:
        print("\nA log citation is a claim about provenance, not a measurement. It "
              "says the number was taken on that date and deliberately not re-run, "
              "and it is worth exactly as much as the ledger it came from.")
    if unverified:
        print("\nEach untraced claim is either: measured but the artifact was not "
              "supplied, arithmetic (label it as such in the text), or asserted "
              "from memory -- which is the one to fix.")
    if disputed:
        print("\nA disputed claim is the paper's number where an audit recomputed a "
              "different one, or could not check it. State the recomputed value, or "
              "keep the paper's with its caveat and add a row containing the claim "
              "under `## DISPUTED` in the ledger.")
    return 1 if (unverified or disputed) and not a.warn_only else 0


if __name__ == "__main__":
    sys.exit(main())
