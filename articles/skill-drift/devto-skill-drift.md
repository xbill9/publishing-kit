---
title: "Agent Skills Drift: A Feedback Loop for Keeping One True"
published: false
description: "An agent skill goes stale in six separate ways while its checks stay green. A step by step guide to measuring that drift and closing it with a feedback loop, using one publishing skill's own audit."
tags: ai, devtools, productivity, opensource
cover_image: https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/skill-drift/cover.0c041943.jpg
---

This article provides a step by step guide to finding drift in an agent skill and closing it with a repeatable feedback loop. The working example is publishing-kit, an agent skill for Claude Code, Codex and Antigravity that publishes one markdown article to five destinations.

https://github.com/xbill9/publishing-kit

**A skill is a set of claims about a world that keeps moving. Every claim has a shelf life, so maintenance is a loop you run on a schedule.**

---

#### What Is Skill Drift?

A skill is instructions plus scripts, and both describe something outside the skill: an editor, an API, a file format, or another script.

Drift is the distance between what the skill says and what is true today. It grows without any error message, because the skill keeps loading and its checks keep passing.

---

#### Why Does a Green Check Prove So Little?

The kit runs a pre-flight against its own article. On the day of this audit that run exited 0:

```text
$ python3 skills/publishing/scripts/preflight.py articles/publishing-kit-skill/devto-publishing-kit.md --live
all checks passed
```

The same day, a code review of the scripts returned 20 findings and running every generator by hand added 2 more. One of those unpublished live articles.

The pre-flight walks a happy path. An article that never contains a `~~~` block can never show that 8 files mishandle one.

---

#### Step 1 — Measure Install Drift

Hosts install a skill as a snapshot, so the copy a session loads can lag the repository by weeks. Compare the two:

```text
$ grep '"version"' .claude-plugin/plugin.json
  "version": "0.32.0",
$ grep -A4 'publishing@publishing-kit' ~/.claude/plugins/installed_plugins.json | grep version
        "version": "0.28.0",
$ git rev-list --count a49983f..dc4f31f
89
```

Every fix in those 89 commits existed in the repository and in no session. The whole Substack destination was among them.

---

#### Step 2 — Measure Version Drift

A version string identifies a release. It says nothing about whether the content changed, and an updater that compares strings inherits that blind spot.

```text
$ git rev-list --count 631cf11..dc4f31f
29
$ git diff --stat 631cf11 dc4f31f -- skills .claude-plugin | tail -1
 16 files changed, 549 insertions(+), 26 deletions(-)
```

Those 29 commits changed behavior under an unchanged version. Bump the version in the same session as the change, so the update has something to see.

---

#### Step 3 — Find Warnings That Should Be Guards

A warning in a document depends on the next reader. The kit's notes recorded that `--update` pushes the source's `published: false` and takes a live article down. The script still did it and printed `updated`.

```text
$ python3 -m unittest tests.test_regressions.DevtoUpdate
.....
----------------------------------------------------------------------
Ran 5 tests in 0.002s

OK
```

The script now reads the listing first, keeps a live article live, and exits non-zero if the article leaves the published listing.

Search the skill for words like "remember", "always" and "make sure". Each one is a candidate for a guard inside the script.

---

#### Step 4 — Test the Checks Themselves

A check drifts when its logic stops matching what its name promises. The fact checker joined every number in an evidence file into one string of digits:

```python
"".join(["12", "3.4"])     # "123.4", so a claim of 123.4 ms traced
```

Comparing whole numbers fixed that and failed the kit's own article on the next run. Its `320px` had been traced to a file with no 320 in it.

Give every check an input it must reject, and run that input. A check that has never failed tells you nothing about what it can catch.

---

#### Step 5 — Collapse Duplicated Logic

Copies drift apart. At audit time 9 files carried their own logic for a code fence. One handled `~~~`, and the other 8 treated it as prose.

One script therefore saw a code block where the next saw paragraphs, and a fix in one file reached none of the others.

One function now classifies fences, and the repository's rules forbid a second.

---

#### Step 6 — Date Every Claim About a Destination

Destinations change without notice, so an undated claim about one has no expiry. The kit labels each behavioral claim with the day it was taken:

```text
MEASURED 2026-09-01: PUT {"article": {"published": true}} returns 200 and changes nothing.
```

The skill carries 143 of those labels. A date tells a reader how far to trust the claim and tells a reviewer where to look first.

When a claim reverses, keep it visible and write a **Correction** beside it with the new measurement. A quiet edit removes the record that the old belief was ever held, and the next session can repeat it.

---

#### The Feedback Loop

Six kinds of drift, one loop. Each pass turns one surprise into something the next session cannot repeat.

```text
  ┌─► 1 OBSERVE   a real run, a failed publish, a review, a user correction
  │       │
  │   2 MEASURE   reproduce it and archive the output, dated
  │       │
  │   3 ENCODE    guard in the script, test with the failing input,
  │       │       Correction in the reference, one source of truth
  │       │
  │   4 VERIFY    the test fails on the old code and passes on the new
  │       │
  │   5 RELEASE   bump the version, update the install, compare served bytes
  │       │
  └───────┘
```

Step 3 sets the order of preference. Code beats a test, a test beats a document, and a document beats memory, because each one depends less on someone paying attention.

Step 4 keeps the loop true. The regression tests here failed 39 of 44 against the scripts as they stood, and all 44 pass now. A test that passes on broken code proves nothing.

Step 5 is the step most often skipped, and skipping it produced the 89 commit gap from Step 1.

---

#### Compare and Contrast

| Drift | Symptom | Detect with | Close with |
| :--- | :--- | :--- | :--- |
| Install | Sessions run old code | Installed version against the repo | Update, then compare content |
| Version | Updater sees no change | Commits since the last bump | Bump with the change |
| Document | A warning nobody enforces | Search for "remember" and "always" | A guard in the script |
| Check | Green over a real defect | An input the check must reject | A regression test |
| Duplication | Copies disagree | Search for the repeated test | One shared function |
| Destination | A claim goes stale | Oldest dated claims first | Re-measure, write a Correction |

---

#### How Often Should the Loop Run?

Run the loop on three triggers:

- 🟢 **Every failed or awkward run.** A retry is the cheapest signal available, so write it down while it is fresh.
- 🟢 **Every release.** Run the tests, run the live pre-flight, bump the version and update the install.
- 🟢 **On a calendar.** A review reads the code cold and catches what a passing run cannot. It also finds claims that no recent run touched.

Give the calendar review to a reader with no stake in the code. Hand it the code and withhold your conclusions, so it can disagree.

---

#### So, Which One First?

Start with install drift. It takes one command, and until it is closed every other fix stays out of reach of your sessions.

Then add one rejecting input to the check you trust most. If that check accepts bad input, you have learned what your green runs are worth.

---

#### Summary

The goal of this article was to find and close drift in an agent skill. The key to the solution was treating every claim as perishable and every surprise as input to a loop. The publishing-kit results were:

- 🟢 22 defects surfaced on a day when the pre-flight passed
- 🟢 44 regression tests now keep the failing inputs, each beside a passing case
- ❌ The installed skill was 89 commits behind the repository
- ⚠️ The `--update` guard is tested against a fake API, and no live article has gone through it yet

Scope: one skill, one repository and one audit on 2026-10-31. Counts come from that repository's git history, and the defects come from one code review and one manual run, so they are a lower bound on what remains.

With this approach a skill stays true for as long as someone keeps running the loop. The full source and every measurement are in the repository.

#### References

- [publishing-kit](https://github.com/xbill9/publishing-kit)
- [The skill's own instructions](https://github.com/xbill9/publishing-kit/blob/main/skills/publishing/SKILL.md)
- [Evidence for this article](https://github.com/xbill9/publishing-kit/tree/main/articles/skill-drift)
