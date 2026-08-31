#!/usr/bin/env python3
"""Run every check for an article, in one command, with one exit code.

The checks in this kit accumulated one at a time, and by the fourth one the
procedure was five commands with different flags that had to be remembered in the
right order. A checklist you have to remember is a checklist you half-run: this
session shipped an article whose own figures were stale while every check it
happened to run came back green.

    preflight.py <article>.md [--live] [--repo-root ..] [--evidence evidence/]

  check-facts.py    every number traces to an artifact
  check-article.py  cover, geometry, crop, committed, front matter, wraps, links
  check-links.py    --live only: fetch every URL and compare bytes to disk
  make-linkedin.py  the announcement's links resolve

--live needs the network and is the only check that sees what a reader sees.
Everything else reasons about local state, and local state has been wrong.
"""

import argparse
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent


def run(label, argv):
    print(f"\n{'=' * 62}\n{label}\n{'=' * 62}")
    r = subprocess.run([sys.executable] + argv, capture_output=True, text=True)
    out = (r.stdout or "").rstrip()
    if out:
        print(out)
    if r.stderr.strip():
        print(r.stderr.rstrip())
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--repo-root", default="..")
    ap.add_argument("--evidence", default="evidence/")
    ap.add_argument("--live", action="store_true",
                    help="also fetch every published URL and compare bytes")
    ap.add_argument("--pinned", action="store_true",
                    help="with --live, resolve at HEAD's sha to bypass the CDN cache")
    a = ap.parse_args()

    art = str(pathlib.Path(a.article))
    results = {}

    results["facts"] = run("check-facts.py — every number traces to an artifact",
                           [str(HERE / "check-facts.py"), art, "--evidence", a.evidence])
    results["article"] = run("check-article.py — cover, crop, committed, wraps, links",
                             [str(HERE / "check-article.py"), art, "--repo-root", a.repo_root])
    if a.live:
        argv = [str(HERE / "check-links.py"), art]
        if a.pinned:
            argv.append("--pinned")
        results["links"] = run("check-links.py — what the destination actually fetches", argv)

    linkedin = pathlib.Path(art).parent / "links.txt"
    if linkedin.exists():
        results["linkedin"] = run("make-linkedin.py — the announcement's links resolve",
                                  [str(HERE / "make-linkedin.py"), art])

    print(f"\n{'=' * 62}\nSUMMARY\n{'=' * 62}")
    for k, v in results.items():
        print(f"  {'PASS' if v == 0 else 'FAIL'}  {k}")
    bad = [k for k, v in results.items() if v]
    if bad:
        print(f"\n{len(bad)} check(s) failed: {', '.join(bad)}")
    else:
        print("\nall checks passed")
    if not a.live:
        print("\nNOTE: --live was not run. Nothing here fetched a published URL,")
        print("and local state has been wrong before. Run --live before publishing.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
