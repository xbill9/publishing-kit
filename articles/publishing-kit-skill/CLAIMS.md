# Claim ledger

Every factual claim in the four versions of this article, and what it traces to.
Two categories only:

  MEASURED   produced by the run of 2026-08-31 that generated these artifacts,
             archived in this directory
  LOG        carried from the kit's own measurement log with the date it was
             taken, and NOT re-measured here

Anything that could not be put in one of those two categories was cut.

## MEASURED 2026-08-31 — archived here

| Claim | Artifact |
| --- | --- |
| Claude Code 2.1.251, Python 3.13.14, Pillow 12.3.0, Linux x86_64 | `environment.txt` |
| `marketplace add` and `plugin install` succeed; wording of both outputs | `plugin-install.txt` |
| publishing 0.1.0, user scope, enabled; 1 skill, 0 agents, 0 hooks, 0 MCP servers | `plugin-install.txt`, `skill-footprint.txt` |
| ~187 tokens always-on, ~8k on-invoke, at 0.2.0 | `skill-footprint.txt` |
| description 528 chars; SKILL.md 446 lines, 22,602 chars | `skill-footprint.txt` |
| references 226 / 148 / 86 / 66 lines; six scripts 1,389 lines; 2,370 total | `skill-footprint.txt` |
| install is a snapshot: different inodes, marker does not propagate | `install-is-a-snapshot.txt` |
| install pinned at commit f7eaac2, equal to HEAD | `install-is-a-snapshot.txt` |
| gde = 11939, aws-builders = 2794 | `devto-orgs.txt` |
| 40 articles listed: gde 24, aws-builders 13, none 3 | `devto-orgs.txt` |
| `GET /api/articles/<id>` 404s while the article lists normally (4531065) | `toolchain-run.txt` header, listing in `devto-orgs.txt` |
| front matter is stored inside `body_markdown` | `devto-roundtrip.txt` |
| 23 of 23 opening fences carry a language label in a stored body | `devto-roundtrip.txt` |
| covers: 1376x768 105 KB / 1376x768 104 KB / 1200x675 15 KB | `toolchain-run.txt` |
| `--tile "-embed.html\|..."` fails with `expected one argument` | `toolchain-run.txt` |
| make-medium: 5 tables, 1 diagram, 19 `<h4>` + 1 `<h1>`, embed 497 KB | `toolchain-run.txt` |
| no `--cover` picks `devto-cover-aws.jpg` for the GDE article | `toolchain-run.txt` |
| default `--img-base` resolves to `gemma4-dev/main/publishing-kit-skill/` | `toolchain-run.txt` |
| Builder payload 22,542 chars / 22.0 KB, 521 lines before unwrap, 408 after | `builder-payload.txt` |
| LinkedIn post 1,269 chars, hook 80 chars; all six checks fire on their failure paths | `linkedin-run.txt` |
| article file sizes | `builder-payload.txt` |
| `sed '1,2d'` leaves the subtitle line behind | `toolchain-run.txt` |
| check-article exits 1 on uncommitted covers and images | `toolchain-run.txt` |
| check-facts reads `127.0.0.1` as version `127.0.0` | `toolchain-run.txt`, `.factsignore` |
| the repo is public and main serves the marketplace manifest (HTTP 200) | `toolchain-run.txt` |

## MEASURED 2026-09-16 — re-measured later, archived here

check-facts gained a `count` pattern on 2026-09-10 and immediately reported the
kit's own headline number untraced. It had no row in this ledger at all: not
MEASURED, not LOG, not cut. It does now, against the live article.

| Claim | Artifact |
| --- | --- |
| dev.to breaks at every wrap: 47 of 62 paragraph-level blocks (58 `<p>` + 4 `<li>`) carry `<br>` | `devto-hardwrap.txt` |
| the source asks for none of them: 0 lines end in two spaces | `devto-hardwrap.txt` |
| the article measured is `.../the-cheapest-cuda-gpu-on-aws-has-an-arm-cpu-...` (4531800), published 2026-08-31 | `devto-hardwrap.txt` |

## Read from the source, not asserted

| Claim | Where it is verifiable |
| --- | --- |
| the eight pre-flight checks and their order | `scripts/check-article.py` docstring and body |
| check-facts traces price, measurement, quantity, version, cloud-id, digest, arch, capacity | `scripts/check-facts.py` PATTERNS |
| check-facts strips fenced code before extracting | `scripts/check-facts.py`, `re.sub(r"```.*?```", ...)` |
| `.factsignore` is substring match, one per line, `#` comments | `scripts/check-facts.py` |
| the no-cover fallback skips covers with `builder` in the name | `scripts/make-medium.py` `__main__` |
| `DEFAULT_REPO` is hardcoded and uses the directory's last segment | `scripts/make-medium.py` `default_img_base` |
| serve-body unwraps paragraphs and leaves code, tables, lists, headings | `scripts/serve-body.py` `unwrap` |
| `--mode builder` defaults to text-free and warns above 2 MB | `scripts/make-cover.py` `__main__` |

## DOCUMENTED — first-party vendor documentation, cited, not measured

LinkedIn is the one destination whose behaviour cannot be measured without
publishing, so these come from LinkedIn's own developer documentation.

| Claim | Source |
| --- | --- |
| The Posts API cannot create a draft: `PUBLISHED` is the only state accepted on creation | Posts API, `lifecycleState` |
| The self-serve API says the same: "the lifecycleState will always be `PUBLISHED`" | Share on LinkedIn |
| Post text is `commentary` in `little` format; elements are text, mentions, hashtags only | little Text Format |
| Every reserved character must be backslash-escaped even outside an element | little Text Format |
| Reserved set `\| { } @ [ ] ( ) < > # \ * _ ~` | little Text Format, Text grammar |
| Mentions match by name, case sensitive; organizations must match the full name | Posts API |
| `w_member_social` is granted self-serve by the "Share on LinkedIn" product | Share on LinkedIn |
| 150 requests per member per day, 100,000 per application per day | Share on LinkedIn, Rate Limits |
| Medium and AWS Builder Center have no publishing API | absence; neither vendor documents one |

## NOT first-party, and labelled as such in the text

| Figure | Value | Status |
| --- | --- | --- |
| LinkedIn post character limit | 3,000 | third-party consensus; LinkedIn documents only `FIELD_LENGTH_TOO_LONG` |
| "…see more" fold | ~140 mobile, ~210 desktop | third-party; moves with screen and font size |

## LOG — carried from the kit's log, dated, not re-measured

| Claim | Date on the log entry |
| --- | --- |
| Medium strips `data:` URIs on paste; 0 of 4 embed, 4 of 4 hosted | 2026-08-30 |
| a cover is met at a 320px feed card (`make-cover.py`, `CARD_W`) | 2026-08-31 |
| Medium's importer strips tables and flattens `<pre>`, drops `<br>` | 2026-08-23 |
| first body image becomes the story cover; title never transfers | 2026-08-23 / 2026-08-30 |
| `#` and `##` both render at title size | 2026-08-23 |
| a forked generator shipped 19 `<h2>` | 2026-08-30 |
| dev.to keeps the first four tags | 2026-08-30 |
| `PUT` does not change the slug of a published article | 2026-08-30 |
| organization_id survives a later update; old URL keeps resolving | 2026-08-30 |
| clipboard race put another article in a draft twice | 2026-08-30 |
| base64 through a JS bridge lost 40 characters of 3,192 | prior run, recorded in `serve-body.py` |
| CSP, `file://` and `wl-copy`/`xclip` are all closed | prior run, recorded in `serve-body.py` |
| `execCommand("delete")` no-ops; the paste then appends | 2026-08-30 |
| Builder Center preserves source newlines inside a paragraph | 2026-08-30 |
| Builder Center field limits 255 / 512, five tags, fixed vocabulary | 2026-08-30 |
| `/create/content/<id>` creates a new empty draft | 2026-08-30 |
| cover 1200x675, 2 MB cap, "text in images is not recommended" | 2026-08-30 |
| check-facts against binaries: 15/0 became 14/1; `4.35 s` matched `4.355` | prior run, recorded in SKILL.md |
| the EC2 host CPU vendor error found by archiving the artifact | prior run, recorded in SKILL.md |

## Cut for want of an artifact

| Claim as first drafted | Why it went |
| --- | --- |
| "19 KB of markdown" in the Builder Center title | measured 19.7 KB after the rewrite; title says 20 KB |
| "alphabetically first is the builder cover, so it ships" | the script skips builder-named covers; the real hazard is the AWS cover on the GDE story, and that was then measured |
| "Medium renders every box-drawing diagram" as written of the first draft's ASCII diagram | the renderer keys on box-drawing characters; the diagram was redrawn and then rendered |

## Traps this ledger walked into

| What happened | Fix |
| --- | --- |
| `claims.md` was first written into `evidence/`, and every claim then traced to it — the ledger restates the numbers, so it matches by construction | moved to `CLAIMS.md`, beside the articles and outside `--evidence` |
| a first read of the published article's fences counted 23 bare ones and looked like counter-evidence to the relabelling claim | they were closing fences; parsed as pairs, 0 of 23 openers are bare, which supports the claim |
| the quoted `serve-body.py` output kept going stale, because editing the number changes the file it measures | iterated until the digit count stopped changing, so the quoted figure is exact |
| the covers and every Medium image resolve over HTTPS and match locally byte for byte | verified after the push, sha256 compared |
| dev.to proxies the cover rather than re-hosting it: `media2.dev.to/dynamic/image/.../<urlencoded source URL>` | `GET /api/articles/me`, three published articles |
| `--content-address` is idempotent: identical bytes give the identical name | `toolchain-run.txt` |
| Builder payload 23,214 chars / 22.7 KB, 531 lines before unwrap, 411 after | `builder-payload.txt` |

## Corrections

**Correction (2026-11-16).** Four rows above cite evidence files that were re-captured after the row was
written, so the file no longer holds the row's number. The rows stay as written; the evidence wins:

| Row | What the evidence holds now |
| --- | --- |
| install pinned at commit f7eaac2 | `install-is-a-snapshot.txt` (re-captured at 0.6.0): pinned and HEAD both `920fe6c` |
| covers: 1376x768 105 KB / 1376x768 104 KB / 1200x675 15 KB | `toolchain-run.txt`: 106890 / 106731 / 15470 bytes, no dimensions for the two dev.to covers; 106890 bytes is 104.38 KiB or 106.89 kB |
| Builder payload 22,542 chars / 22.0 KB | `builder-payload.txt`: 23234 chars |
| Builder payload 23,214 chars / 22.7 KB | `builder-payload.txt`: 23234 chars |

None of these numbers appears in the article.

**Correction (2026-11-16), the article.** Five sentences in `devto-publishing-kit.md` said more than their
evidence. Found by running research-kit's math-sandbox, ablation-stat-auditor and figure-forensics skills
on this directory.

| Was | Now | Evidence |
| --- | --- | --- |
| a stray break in every paragraph | in most paragraphs | `devto-hardwrap.txt`: 47 of 62 blocks; 15 had none |
| a 1376x768 cover loses 95px off the top and bottom | would lose; the kit renders dev.to covers at 1376x578 | every dev.to cover in this directory is 1376x578, which the 1000x420 crop leaves whole |
| The two numbers on the cover are real | These two numbers are real | neither `cover.77acc7c4.jpg` nor `cover.ae4d639e.jpg` carries them; they are in the table |
| measured on 2026-08-31 | measured between 2026-08-30 and 2026-09-16 | `devto-hardwrap.txt` 2026-09-16, `devto-cover-crop.txt` 2026-09-10, Medium data URIs from the log at 2026-08-30 |
| repo copy stays readable at 95 columns | keeps its line wrapping | 20 of 106 prose lines were longer than 95 characters, the longest 126 |

The Medium row of the table ("0 of 4 ... 4 of 4") is now labelled as the kit log of 2026-08-30. It has no
archived artifact and was not re-measured.

## DISPUTED

Claims that research-kit's audits (`math-sandbox` `eq_verified_numbers.json`, `ablation-stat-auditor`
`stat_audit.json`, in xbill9/claude-research-skills `examples/publishing-kit-article/`) mark MISMATCH or
NOT CHECKABLE, kept in the article with the reason here.

| Claim | Audit record | Why it stays |
| --- | --- | --- |
| 0 of 4 | E3_medium_data_uri_0_of_4, NOT CHECKABLE | no archived artifact; the article labels it "kit log, 2026-08-30" |
| 4 of 4 | E3_medium_data_uri_0_of_4, NOT CHECKABLE | same row as 0 of 4 |
| 320px | D3_card_width_is_devto, NOT CHECKABLE | `CARD_W` in make-cover.py; no archived measurement of dev.to's card width |
| 2.381:1 | M5_substack_source_shape | number collision: 1000/420 = 2.380952 is VERIFIED as D1_proxy_ratio; the match is a 1 in M5's code-block line counts |
| 95px | M1_own_source_95_columns | number collision: the crop is VERIFIED at 95.04 px a side; M1 is the 95-column source wrap |
