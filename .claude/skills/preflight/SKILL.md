---
name: preflight
description: Run the full pre-flight check chain on an article in this repo and report PASS/FAIL per check. Use before committing a change to scripts/ or before publishing an article.
disable-model-invocation: true
---

Run the kit's pre-flight checks on an article and report the result per check.

## Which article

`$ARGUMENTS` is the article path, optionally followed by extra flags. If no
article is given, default to the dogfood article, which is this repo's
regression test:

```
articles/publishing-kit-skill/devto-publishing-kit.md
```

## Run it

From the repo root:

```bash
python3 skills/publishing/scripts/preflight.py <article> --live
```

Always pass `--live` unless the user asked not to: it is the only check that
fetches every published URL and compares served bytes to disk. Without it the run
reasons purely about local state, and local state has been wrong. Add `--pinned`
if a link check fails in a way that looks like a stale CDN copy — it resolves at
HEAD's sha to bypass the cache.

Do not pass `--repo-root` or `--evidence` unless the user names them. Their
defaults derive from the article's own location (the git root containing it, and
`<article dir>/evidence`), which is the correct behavior; overriding them with
cwd-relative values is how this kit once produced clean passes over nothing.

## What it runs

| check | what it proves |
|---|---|
| `check-facts.py` | every number in the article traces to an artifact in `evidence/` |
| `check-article.py` | cover exists, geometry and crop are right, cover is committed, front matter, wraps, links |
| `check-links.py` | `--live` only: fetch every URL, compare bytes to disk, and check every rendered link the way Builder Center's publish gate does |
| `make-linkedin.py --no-write` | the announcement's links resolve (`--no-write` because a check must not rewrite what it checks) |

The last one runs only when `links.txt` sits beside the article.

## Sidecars it depends on

Beside the article: `links.txt` (`key = url`; a `PENDING` value is a deliberate
failure), `linkedin.args`, `.factsignore` (one claim per line, each with its
reason in a comment above it), `evidence/` (text artifacts only — pointing it at
binaries yields coincidental digit matches and a false green), `CLAIMS.md`.

## Reporting

Quote preflight's own PASS/FAIL summary and its exit code rather than
recomputing or summarizing the counts yourself. If it exits non-zero, name which
check failed and the specific line of its output that says why; do not describe
a failing run as passing, and do not treat a missing `--live` nag as a pass.
