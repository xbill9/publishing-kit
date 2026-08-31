#!/usr/bin/env python3
"""Measure the skill's own size and cost, so an article about it cannot go stale by hand.

An article that documents this kit states the kit's line counts and token cost.
Every commit to the kit invalidates them, and patching them by hand is how they
drift -- which happened three times while writing the first such article.

    skill-footprint.py                 # human-readable, for evidence/
    skill-footprint.py --markdown      # the table, to paste into an article
    skill-footprint.py --footer        # the one-line cover footer

`claude plugin details` reports the token projection, but it reads the INSTALLED
snapshot, not the worktree. It is included only when --installed is passed and it
is labelled with the version it actually measured, because a stale projection
presented as current is exactly the failure this script exists to stop.
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def counts():
    skill = ROOT / "SKILL.md"
    refs = sorted((ROOT / "references").glob("*.md"))
    tmpl = sorted((ROOT / "templates").glob("*"))
    scripts = sorted(p for p in (ROOT / "scripts").glob("*.py"))
    n = lambda p: len(p.read_text().splitlines())
    return {
        "skill": (skill.name, n(skill)),
        "references": [(p.name, n(p)) for p in refs],
        "templates": [(p.name, n(p)) for p in tmpl],
        "scripts": [(p.name, n(p)) for p in scripts],
        "description_chars": len(re.search(
            r"^description:\s*(.*)$",
            re.match(r"^---\n(.*?)\n---\n", skill.read_text(), re.S).group(1),
            re.M).group(1)),
    }


def total(c):
    return (c["skill"][1] + sum(x for _, x in c["references"])
            + sum(x for _, x in c["templates"]) + sum(x for _, x in c["scripts"]))


def version():
    j = json.loads((ROOT.parent.parent / ".claude-plugin" / "plugin.json").read_text())
    return j["version"]


def installed_cost():
    """Only ever reported with the commit it measured.

    Comparing VERSION strings is not enough and this script made that mistake
    first: the content changed across several commits while plugin.json still
    said 0.2.0, so a version check called a stale snapshot current. The installed
    record carries gitCommitSha; compare that against HEAD, the same way
    check-article.py compares a cover against HEAD rather than trusting that it
    is tracked.
    """
    try:
        out = subprocess.run(["claude", "plugin", "details", "publishing"],
                             capture_output=True, text=True, timeout=60).stdout
        row = re.search(r"publishing\s+(~\S+)\s+(~\S+)", out)
        if not row:
            return None
        rec = json.loads((pathlib.Path.home() / ".claude/plugins/installed_plugins.json")
                         .read_text())["plugins"]["publishing@publishing-kit"][0]
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        return (rec.get("gitCommitSha", "?"), head, row.group(1), row.group(2))
    except Exception:
        return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--markdown", action="store_true")
    p.add_argument("--footer", action="store_true")
    p.add_argument("--installed", action="store_true",
                   help="also query the INSTALLED plugin's token projection")
    a = p.parse_args()
    c = counts()
    t = total(c)
    v = version()

    if a.footer:
        print(f"publishing {v} - 1 skill, {len(c['references'])} references, "
              f"{len(c['scripts'])} scripts, {t:,} lines")
        return 0

    if a.markdown:
        print("| Component | Lines |")
        print("| --- | --- |")
        print(f"| `{c['skill'][0]}` | {c['skill'][1]} |")
        for name, k in c["references"]:
            print(f"| `references/{name}` | {k} |")
        for name, k in c["templates"]:
            print(f"| `templates/{name}` | {k} |")
        print(f"| {len(c['scripts'])} scripts | {sum(x for _, x in c['scripts']):,} |")
        print(f"| **total** | **{t:,}** |")
        return 0

    print(f"# skill footprint, worktree, publishing {v}")
    print(f"\n{c['skill'][0]}: {c['skill'][1]} lines, "
          f"description {c['description_chars']} chars")
    for label, items in (("references", c["references"]),
                         ("templates", c["templates"]),
                         ("scripts", c["scripts"])):
        print(f"\n{label} ({len(items)}):")
        for name, k in items:
            print(f"  {k:>5}  {name}")
    print(f"\ntotal: {t:,} lines")
    if a.installed:
        got = installed_cost()
        if got:
            sha, head, always, invoke = got
            fresh = sha == head
            print(f"\ninstalled snapshot {sha[:7]} (HEAD is {head[:7]}): "
                  f"{always} always-on, {invoke} on-invoke")
            if not fresh:
                print("  STALE -- that projection measures an older commit. Run:")
                print("  claude plugin marketplace update publishing-kit && "
                      "claude plugin update publishing")
        else:
            print("\ninstalled plugin: not queryable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
