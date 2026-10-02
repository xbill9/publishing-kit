---
title: "Write Markdown Once, Publish It Everywhere: dev.to, Medium, AWS Builder Center and LinkedIn"
published: false
description: "Markdown is easy to write and hard to publish. Every destination renders it differently, two have no API, and the failures show up only after you hit Publish. A step by step walk-through of publishing-kit, an agent skill that builds, checks and posts each version, used here to publish this article."
tags: writing, markdown, devtools, ai
cover_image: https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/markdown-publishing-woes/cover.8a6ca645.jpg
---

This article provides a step by step guide to publishing one markdown article to dev.to, Medium, AWS Builder Center and LinkedIn with publishing-kit, an agent skill for Claude Code, Codex and Antigravity. The article you are reading was published with it, and every command output below comes from that run.

https://github.com/xbill9/publishing-kit

**One markdown file goes in. A dev.to draft, a Medium story, a Builder Center draft and a LinkedIn post come out, each one checked before it ships.**

---

#### What Is the Problem?

Markdown is the easy part. You write headings, a table, a few code blocks and a cover image, and it looks right in your editor and on GitHub.

Then you publish it in four places, and each one treats that file differently:

| Destination | Publishing API | Tables | Multi-line code | Cover |
| :--- | :--- | :--- | :--- | :--- |
| dev.to | 🟢 full REST API | 🟢 native | 🟢 native | URL, cropped to 2.381:1 |
| Medium | ❌ unsupported since 2023 | ❌ dropped | ❌ one line | first image in the body |
| AWS Builder Center | ❌ none | 🟢 native | 🟢 line-numbered | 1200x675 upload |
| LinkedIn | ⚠️ posts only, no drafts | ❌ none | ❌ none | link card or upload |

Every one of those differences fails without an error. You get a plausible-looking page with a missing table, a code block run together on one line, or a cover with its title cut off, and you see it after it is live.

---

#### Why Is Medium So Inconsistent?

Medium has two ways in, and they disagree with each other.

**The importer** (`medium.com/p/import`) brings in prose, headings, links and images from a URL. It drops markdown tables entirely, flattens `<pre>` blocks to a single line, strips HTML comments, and renders only two heading sizes, so `##` sections all read as titles. A link inside an image caption makes the whole image disappear. It also caches by URL and ignores the query string, so re-importing a fixed page with `?v=2` brings back the old one.

**Pasting into the editor** keeps multi-line code, but removes any image embedded as a `data:` URI, with no placeholder left behind.

**The API** would avoid all of this, and Medium's own documentation now opens with *"The Medium API is no longer supported. We do not recommend using it."* The repository was archived in 2023.

So Medium can only be reached by driving its editor in a browser, with its quirks known in advance.

---

#### And the Other Three?

**dev.to** has a complete REST API: create, update, list, and route to an organization. It renders markdown with hard line breaks on, so a source file wrapped at 80 columns publishes with a break in the middle of every paragraph. It displays the cover through a 2.381:1 crop, which cuts the top and bottom off a 16:9 image. And an update through the API sends the front matter's `published: false` along with the body, which takes a live article back to draft.

**AWS Builder Center** has no publishing API. The body goes in by pasting into a browser editor, and its publish step checks every link, including URLs written as plain text, and refuses with a message that names none of them.

**LinkedIn** has a Posts API, but `PUBLISHED` is the only state it accepts on creation, so anything posted through it goes straight to your feed. The post text renders no markdown at all.

---

#### What Does publishing-kit Do?

It packages the workarounds as an agent skill plus a set of small Python scripts. The skill tells the agent what each destination needs; the scripts do the parts that should be exact.

- **One source, four artifacts.** The dev.to markdown is the source. `make-medium.py` renders tables to images and writes Medium HTML, `make-builder.py` writes the Builder Center version, `make-linkedin.py` writes the post.
- **Covers at the size that is shown.** `make-cover.py` draws one design at every geometry the destinations need and names each file by a hash of its bytes.
- **A pre-flight that fails the build.** `preflight.py` checks the cover, the front matter, the prose, the links and every number in the article, and exits non-zero.
- **The API where one exists.** `publish-devto.py` posts to dev.to with no browser.
- **Browser helpers where none does.** Small in-page scripts for the Medium and Builder Center editors that refuse to act when something looks wrong.

---

#### At This Point You Should Have…

- Claude Code, Codex or Antigravity, with browser automation for the Medium and Builder Center steps.
- Python 3 with Pillow, and `pandoc` for the Medium build.
- A public GitHub repository for the article's directory. Covers and Medium images are fetched by URL, so they must be pushed before you publish.
- A dev.to API key in `~/.devto.key` or `$DEV_TO_API_KEY`.
- Signed-in browser sessions for Medium, Builder Center and LinkedIn.

---

#### Step 1 — Install the Skill

In Claude Code:

```shell
/plugin marketplace add xbill9/publishing-kit
/plugin install publishing@publishing-kit
```

In Codex:

```shell
codex plugin marketplace add xbill9/publishing-kit
codex plugin add publishing@publishing-kit
```

When you want to run a script by hand, ask the skill where it lives:

```shell
python3 skills/publishing/scripts/skill-footprint.py --where
```

```text
/home/xbill/publishing-kit/skills/publishing
```

Most of the time you do not run the scripts yourself. You ask the agent to publish, and it runs them.

---

#### Step 2 — Write the Source Article

The source is a dev.to markdown file with front matter, because dev.to renders tables, code and emoji natively. Everything else is derived from it. This is the front matter of this article:

```yaml
---
title: "Write Markdown Once, Publish It Everywhere: dev.to, Medium, AWS Builder Center and LinkedIn"
published: false
description: "Markdown is easy to write and hard to publish. ..."
tags: writing, markdown, devtools, ai
cover_image: https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/markdown-publishing-woes/cover.8a6ca645.jpg
---
```

`published: false` stays in the file. Going live is a separate command, so a routine update never publishes by accident.

The prompt that started this article was one sentence: *"write another article that explains what this skill does, step through how to use it and publish it, and dogfood the article with the kit."*

---

#### Step 3 — Make the Cover

```shell
python3 make-cover.py --out cover.jpg --sizes devto,builder --flow \
  --source "article.md|one markdown file" \
  --dest "dev.to|REST API|blue" --dest "Medium|browser|orange" \
  --dest "Builder Center|browser|orange" --dest "LinkedIn|composer|muted" \
  --headline "Write once|publish everywhere" \
  --content-address --url-base "https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/markdown-publishing-woes"
```

```text
wrote cover.8a6ca645.jpg  1376x578  61 KB
wrote cover-builder.ebbc48ba.jpg  1200x675  52 KB
  https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/markdown-publishing-woes/cover.8a6ca645.jpg
  https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/markdown-publishing-woes/cover-builder.ebbc48ba.jpg
```

One design, two sizes: 1376x578 for dev.to, which is exactly the 2.381:1 shape it displays, and 1200x675 for Builder Center's upload. The hash in each filename means a regenerated cover is a new URL, so no cache can serve the old picture.

---

#### Step 4 — Commit and Push

```shell
git add articles/markdown-publishing-woes
git commit -m "articles: write once, publish everywhere"
git push
```

dev.to fetches the cover from its URL every time the page renders, and Medium fetches the table images when it imports. A file that exists only on your disk shows up as a broken image.

---

#### Step 5 — Run the Pre-Flight

```shell
python3 preflight.py devto-markdown-publishing-woes.md --live
```

```text
==============================================================
SUMMARY
==============================================================
  PASS  facts
  PASS  prose
  PASS  article
  PASS  links
  FAIL  linkedin

1 check(s) failed: linkedin
```

At this point the only failure is the LinkedIn post, because its links to the Medium and Builder Center versions are still `PENDING`. Everything the dev.to draft needs has passed.

`--live` fetches every published URL and compares the served bytes with the file on disk, and fetches every link in the article the way Builder Center's publish step does. Without it the checks reason only about local files.

---

#### Step 6 — Post to dev.to Through the API

```shell
python3 publish-devto.py --create devto-markdown-publishing-woes.md --org-slug gde
```

```text
  ok    published: false
  ok    title present
  ok    description present
  ok    tags present
  ok    devto-markdown-publishing-woes-hosted.html image URLs resolve to markdown-publishing-woes
  ok    3 medium/img image(s) committed and matching HEAD
  ok    no hard-wrapped paragraphs
  ok    no stale counts of the kit's own parts
  ok    no empty link targets

0 fail, 0 warn

created 4788671
   4788671  draft      org=-               Write Markdown Once, Publish It Everywhere: dev.to, 
            https://dev.to/xbill/write-markdown-once-publish-it-everywhere-devto-medium-aws-builder-center-and-linkedin-48m7-temp-slug-1340266
  routed to gde (11939)
```

`--create` runs the article checks first and refuses on any failure. The front matter is part of the payload, so the title, tags and cover arrive with the body, and the paragraphs are unwrapped on the way out. The result is a draft.

---

#### Step 7 — Build the Medium Version

```shell
python3 make-medium.py devto-markdown-publishing-woes.md medium --cover=cover.8a6ca645.jpg
```

```text
devto-markdown-publishing-woes.md: 2 tables, 0 diagrams
   USE THIS   -> medium/devto-markdown-publishing-woes-hosted.html  (paste or import; needs medium/img committed AND pushed)
   not this   -> medium/devto-markdown-publishing-woes-embed.html   (223 KB; data: URIs, Medium drops them all on paste)
   Medium never fills its Title field from pasted content -- set the title separately.
```

Both tables in this article are now PNGs under `medium/img/`, rendered at twice the display size. `-hosted.html` points at them by their public GitHub URL, so Medium fetches and re-hosts them. Code blocks stay as code, because pasting keeps multi-line code where the importer would flatten it.

The agent then opens Medium in the browser and pastes the hosted HTML into a new story. The title is typed into its own field, because no paste or import route fills it.

---

#### Step 8 — Build the Builder Center Version

```shell
python3 make-builder.py devto-markdown-publishing-woes.md --out builder-markdown-publishing-woes.md \
  --title "Write Markdown Once, Publish It Everywhere"
```

```text
  ok    no emoji
  ok    widest table is 5 columns
  ok    no duplicate AWS disclaimer (the platform adds its own)
  ok    title and subtitle carried as strippable lines
```

Emoji come out, because Builder Center's house style has none, and front matter comes out, because title and description are separate fields there. The agent serves the body from `serve-body.py` on the same machine, carries it into the editor tab in `window.name`, compares a checksum on both sides, checks that the editor is empty, and pastes once.

---

#### Step 9 — Write the LinkedIn Post

```shell
python3 make-linkedin.py devto-markdown-publishing-woes.md
```

```text
devto-markdown-publishing-woes.md -> linkedin-devto-markdown-publishing-woes.txt
  FAIL  3 link(s) still PENDING: builder, devto-gde, medium
  ok    no draft URLs; every slug is settled
  ok    hook fits the fold: 91 chars
  ok    post is 832 chars of 3000
  ok    no markdown left; LinkedIn renders none of it
  ok    no template scaffolding left
  ok    no Unicode pseudo-bold
```

The post is a text file plus the cover fitted to LinkedIn's image size. Its links come from `links.txt` beside the article, and a link still marked `PENDING` fails the run, so a post cannot go out pointing at a page that does not exist yet. The run above is from before the drafts were published; once each destination is live, its URL goes into `links.txt` and the run passes.

---

#### Step 10 — Publish

Every destination is now a draft. `--list` shows the dev.to one, already routed to the organization:

```shell
python3 publish-devto.py --list
```

```text
30 draft(s)
   4788671  draft      org=gde             Write Markdown Once, Publish It Everywhere: dev.to, 
            https://dev.to/gde/write-markdown-once-publish-it-everywhere-devto-medium-aws-builder-center-and-linkedin-48m7-temp-slug-1340266
```

Going live is one deliberate step per destination. For dev.to it is `publish-devto.py --publish 4788671`. dev.to ignores a `published: true` sent on its own, so `--publish` resends the body with the front matter flipped and then confirms from your article listing. Medium and Builder Center are one click on Publish in the browser, and the LinkedIn post is pasted into the composer with the cover attached.

---

#### 🔎 Tip: Keep `published: false` in the Source

The pre-flight requires it, and it is what makes an update safe. After updating an article that is already live, run `--publish <id>` again and check `--list`, because the update carried the draft flag with it.

---

#### 🔎 Tip: Let the Agent Drive the Editors

Medium and Builder Center editors reject typed keystrokes in a background tab, hide upload buttons inside shadow DOM, and duplicate a paste if the editor was not empty. The kit's in-page helpers check each of those before acting, so the browser steps are safer in the agent's hands.

---

#### Compare and Contrast

| Destination | How it gets there | Built by | Draft first? |
| :--- | :--- | :--- | :--- |
| dev.to | REST API 🥇 | `publish-devto.py` | 🟢 yes |
| Medium | browser paste | `make-medium.py` | 🟢 yes |
| AWS Builder Center | browser paste | `make-builder.py` | 🟢 yes |
| LinkedIn | composer | `make-linkedin.py` | ⚠️ composer only |

---

#### So, Which One?

Write in dev.to markdown and publish there first. It is the only destination with a complete API, it renders everything the source contains, and its draft link is the first one the other versions can point at. Medium and Builder Center follow from the same file, and the LinkedIn post goes last, once every link it carries resolves.

---

#### Summary

The goal of this article was to explain why publishing markdown to more than one place goes wrong, and to publish this article to four destinations with publishing-kit. The key to the solution was one source file, a generated artifact per destination, and a pre-flight that fails before anything ships. The results were:

- 🟢 **dev.to posted through its API**, title, tags and cover carried in the front matter.
- 🟢 **Medium tables and code rendered to images**, fetched and re-hosted by Medium.
- 🟢 **Builder Center body pasted once**, checksummed on both sides.
- 🟢 **LinkedIn post generated with every link resolving.**
- ⚠️ **Medium and Builder Center still need a browser**, because neither offers a publishing API.
- ❌ **LinkedIn cannot hold an API draft**; the post waits in a file until you paste it.

Scope: one article, published on 2026-10-02 with publishing-kit 0.29.0 from Claude Code on Linux, to the dev.to `gde` organization, Medium, AWS Builder Center and LinkedIn. Destination behaviour described above comes from the dated measurements recorded in the kit's skill and reference files.

The strategy for publishing one markdown article to four destinations with an agent skill was validated with an incremental step by step approach.

---

#### References

* [publishing-kit | GitHub](https://github.com/xbill9/publishing-kit)
* [Medium API documentation (archived) | GitHub](https://github.com/Medium/medium-api-docs)
* [Forem API | dev.to](https://developers.forem.com/api)
* [Posts API | LinkedIn](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api)
* [AWS Builder Center](https://builder.aws.com)
