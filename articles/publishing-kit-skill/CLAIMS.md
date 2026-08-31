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
| ~150 tokens always-on, ~6.6k on-invoke | `skill-footprint.txt` |
| description 433 chars; SKILL.md 376 lines, 18,644 chars | `skill-footprint.txt` |
| references 226 / 86 / 65 lines; five scripts 1,068 lines; 1,821 total | `skill-footprint.txt` |
| install is a snapshot: different inodes, marker does not propagate | `install-is-a-snapshot.txt` |
| install pinned at commit 5da0a03, equal to HEAD | `install-is-a-snapshot.txt` |
| gde = 11939, aws-builders = 2794 | `devto-orgs.txt` |
| 40 articles listed: gde 24, aws-builders 13, none 3 | `devto-orgs.txt` |
| `GET /api/articles/<id>` 404s while the article lists normally (4531065) | `toolchain-run.txt` header, listing in `devto-orgs.txt` |
| front matter is stored inside `body_markdown` | `devto-roundtrip.txt` |
| 23 of 23 opening fences carry a language label in a stored body | `devto-roundtrip.txt` |
| covers: 1376x768 105 KB / 1376x768 104 KB / 1200x675 15 KB | `toolchain-run.txt` |
| `--tile "-embed.html\|..."` fails with `expected one argument` | `toolchain-run.txt` |
| make-medium: 5 tables, 1 diagram, 19 `<h4>` + 1 `<h1>`, embed 485 KB | `toolchain-run.txt` |
| no `--cover` picks `devto-cover-aws.jpg` for the GDE article | `toolchain-run.txt` |
| default `--img-base` resolves to `gemma4-dev/main/publishing-kit-skill/` | `toolchain-run.txt` |
| Builder payload 22,544 chars / 22.0 KB, 521 lines before unwrap, 408 after | `builder-payload.txt` |
| LinkedIn post 1,270 chars, hook 80 chars; all five checks fire on their failure paths | `linkedin-run.txt` |
| article file sizes | `builder-payload.txt` |
| `sed '1,2d'` leaves the subtitle line behind | `toolchain-run.txt` |
| check-article exits 1 on uncommitted covers and images | `toolchain-run.txt` |
| check-facts reads `127.0.0.1` as version `127.0.0` | `toolchain-run.txt`, `.factsignore` |
| the repo is public and main serves the marketplace manifest (HTTP 200) | `toolchain-run.txt` |

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
