# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This repo *is* one plugin containing one skill: `skills/publishing/`. Read
`skills/publishing/SKILL.md` before changing anything under it — it is the
product, and it encodes rules about its own maintenance, not just about the
articles it publishes.

## Verifying a change

There is no CI and no test suite. The regression test is running the kit against
its own dogfood article:

```bash
python3 skills/publishing/scripts/preflight.py \
  articles/publishing-kit-skill/devto-publishing-kit.md --live
```

Run it after touching anything in `scripts/`. `--live` is the only check that
fetches published URLs and compares served bytes to disk; without it the run
reasons about local state, and local state has been wrong. Exit code is 1 if any
check failed. `--pinned` (with `--live`) resolves at HEAD's sha to bypass the CDN
cache.

Linting is `ruff check skills/publishing/scripts/`, configured in `ruff.toml`. The
rule set is narrow on purpose — long measured comments and one-line semicolon
guards are house style, not defects, so those rules are off. A PostToolUse hook
runs it on any `.py` file that gets edited.

## Layout

- **Skills live at `skills/publishing/`, at the repo root — not `.claude/skills/`.**
- Four names must stay equal, all currently `publishing`: the skill directory
  name, `SKILL.md`'s `name:`, `.claude-plugin/plugin.json`'s `name`, and
  `marketplace.json`'s `plugins[].name`.
- `skills/publishing/references/*.md` are loaded on demand by SKILL.md, one file
  per destination. `templates/*.txt` hold post *shape* (`{key}` substitution,
  `[[key]]…[[/key]]` conditionals) — shape belongs there, never in code.
- `references/house-style.md` is the only retargeting seam. Nothing in SKILL.md
  or `scripts/` may depend on its contents.

## Manifests

`.claude-plugin/plugin.json` is canonical and the only file holding `version`.
The root `plugin.json` (the Codex/`agy` host surface) is a **generated copy** —
never hand-edit it; a PostToolUse hook regenerates it when the canonical file
changes. `marketplace.json` carries its own separately-worded description, so a
description change is two files.

## Dependencies (declared nowhere machine-readable)

Most scripts are stdlib-only Python 3. Beyond that: **Pillow** (hard import in
`make-cover.py`; lazy, function-local in `check-article.py`, `make-linkedin.py`,
`make-advocu.py` so checks degrade instead of hard-failing), **`pandoc`** (shelled
out by `make-medium.py`), **`git`**, and **hardcoded absolute font paths** under
`/usr/share/fonts/truetype/{liberation,dejavu}/`. Image generation breaks on a box
without those exact paths. Adding a dependency means updating README's
Requirements section — there is no manifest to update.

## Rules that cost this repo a retry each

- **Never fork a script.** A wrapper *calls* `make-medium.py`; it does not copy
  from it. Unwrapping logic exists once, in `scripts/bodytext.py`.
- **Defaults anchor to the article, not the cwd.** Flags derive from
  `git rev-parse --show-toplevel` of the article's directory. Reintroducing a
  cwd-relative default produces clean passes over nothing.
- **A check must not rewrite the artifact it checks** (hence
  `make-linkedin.py --no-write` inside preflight).
- **Guards belong inside the script.** Each `window.bc` / `window.li` /
  `window.gate` helper in `scripts/browser/*.js` returns `{refused: ...}` rather
  than acting when a precondition fails. An assertion outside the in-page script
  is not a guard.
- **Simulate the destination, do not assert about it.** Checks fetch URLs and
  compute crops; they do not compare against remembered constants.
- **`articles/` is committed output, deliberately.** Covers and Medium images are
  fetched by URL at render time, so commit *and push* before publishing. Cover
  filenames are content-addressed (`cover.77acc7c4.jpg`) — regenerate, never edit
  in place; identical bytes reproduce the identical name.
- Secrets come from `$DEV_TO_API_KEY` or `~/.devto.key`, **never argv** (shell
  history, process listings).
- Never claim a browser draft or post was created when it was not.

## Writing it down is part of the change

- Every non-obvious behavioral claim in SKILL.md and `references/` carries
  `MEASURED <date>`. A claim without one does not belong there.
- A reversal is written as an explicit `**Correction.**` paragraph that keeps the
  retracted claim visible and says why it is now unknown — not a quiet edit.
- When a quirk costs a retry, it is not done until it is in the destination's
  reference section *and* the working route is folded into that destination's
  `scripts/browser/*.js` helper.
- Before adding a check, apply SKILL.md's "three ways this kit has been wrong":
  don't generalize one destination's property into a rule; identity is not
  freshness; a negative result needs a positive control.

## Host-agnostic phrasing

SKILL.md, `references/` and `scripts/browser/` must not name a host or a
host-specific tool. Say "browser automation", not "Claude Code driving Chrome";
name browser *capabilities* (`javascript_tool`, `file_upload`, `find`,
`computer type`, `browser_batch`) as capabilities, not as one host's tool names.
The kit targets Antigravity (`agy`), Codex and Claude Code.

Strings shared between a helper and its docs must move together: the LinkedIn
proxy input's `aria-label` is what the automation's `find` step searches for, so
renaming it in `linkedin-composer.js` is also an edit to `references/linkedin.md`.

## Commits

Subject is `<area>: <lowercase statement of what was measured or what broke>` —
e.g. `publishing: Medium's 403 is not a broken link`, not `fix link check`. Area
is one of `publishing`, `references`, `articles`, `house-style`, `linkedin`,
`advocu`, `check-facts`, `skill`. Version bumps are their own commit whose
subject is the bare version number (`0.26.1`).
