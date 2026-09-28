# Kaggle Benchmarks: the benchmark page an article links to

A Kaggle Benchmarking article links a benchmark page, and that page is part of
what readers and judges see. Everything below was MEASURED 2026-09-28 on
`kaggle.com/benchmarks/<owner>/<slug>`, finishing one entry. Tasks are pushed and
run with the `kaggle` CLI; the benchmark itself (grouping tasks, settings,
description) exists only in the web UI.

Paste `scripts/browser/kaggle-benchmark.js` (`window.kg`) before touching the page.

## The description stays a draft until its section is published

A new benchmark shows a **Description (Draft)** placeholder ("only visible to the
public after you edit and publish it"). The section editor has a **Publish
section** toggle, off by default. Saved with the toggle on, the "(Draft)" label
went away and the text rendered after a reload. Saving with it off was not tried.
Check the page after saving; a draft description leaves a public benchmark with no
summary.

## Typing into the description editor froze the tab

A `computer type` of about 1,100 characters into the description textarea timed
out after 30 s, and screenshots and scripts then timed out for another 15 s or
more; navigating the tab again recovered it. Setting the textarea through the
native value setter and dispatching `input` put all 1,123 characters in, and Save
kept them: `kg.setDescription(TEXT)`.

Opening the editor: the section's pencil is a button labelled `Edit Description
Section`. A click on its accessibility ref only scrolled the section into view;
`.click()` on the element from a script opened the editor
(`kg.openDescription()`).

## Public is permanent, and the signed-out page lags

Settings → Visibility → Public, then **Save Changes**, opens "Make this Benchmark
Public?": permanent, cannot be undone, applies the Apache 2.0 License. After it,
a signed-out request for the benchmark URL still returned 404 for about 15
minutes (the switch at about 11:10 EDT, the first 200 at 11:25 EDT, polled every
30 s), while the public task pages returned 200 throughout. A link checker run in
that window reports the article's main link as broken. Poll until it returns 200
before publishing the article.

## The default overall score ignores numeric tasks

Settings → Overall score defaults to *Percentage of tasks passed*, and the page's
own hint says tasks with a numeric score are ignored. A task that returns a float
(share of questions correct) needs *Average of task scores*.

## The leaderboard shows the latest run, not the best

`kaggle b leaderboard <owner>/<slug> -s` showed 0.0 for models whose earlier run
of the same task version scored 1.0: a later run that failed on the model quota
became the one displayed. A script that reports the best run per model will
disagree with the page. Compare an article's numbers against the latest run of
each (task, model) pair, and never start a run that can fail on the quota over a
pair whose latest run is good.

## Where the quota is shown

The CLI does not report the model quota. The **Add Models** dialog on the
benchmark page shows it in its footer: `Daily AI Quota $6.44 used / $10.00`.
Close the dialog with **Cancel**; nothing changes.
