---
title: "Publishing Markdown to a LinkedIn Article from an Agent Skill"
published: false
description: "LinkedIn's article editor saves two heading levels and no inline code, and its page cannot parse HTML. A step by step walk-through of the LinkedIn article destination in publishing-kit, tested by publishing the kit's own walk-through through it."
tags: linkedin, writing, devtools, ai
cover_image: https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/linkedin-article/cover.dbf080b2.jpg
---

This article provides a step by step guide to publishing a markdown article as a LinkedIn article with publishing-kit, an agent skill for Claude Code, Codex and Antigravity. The LinkedIn article editor joins dev.to, Medium, Substack and AWS Builder Center as a destination, and every output below comes from publishing the kit's own walk-through to LinkedIn through it.

https://github.com/xbill9/publishing-kit

**One markdown file goes in. A LinkedIn article comes out, with every code block, link, heading and character checked against the source after LinkedIn has saved it.**

---

#### What Is the Problem?

A LinkedIn article is the long-form piece at `linkedin.com/article/new/`, published under `/pulse/`. It is separate from the short feed post that announces an article. It goes in through a web editor, and the editor decides what survives.

Pasting HTML into it, then reloading the page so the editor shows what LinkedIn stored, gives this:

| Content | In the saved article |
| :--- | :--- |
| Multi-line code blocks | 🟢 kept, same line counts |
| Images in a figure, on public URLs | 🟢 fetched and re-hosted by LinkedIn |
| Plain links, bold, lists, quotes | 🟢 kept |
| Image alt text | ⚠️ arrives empty; kept once set through the editor |
| Headings | ⚠️ two levels are saved; the others become paragraphs |
| Inline code | ❌ shown in the editor, gone after a reload |
| A link whose text is inline code | ❌ the link is dropped |
| A second paragraph inside a block quote | ❌ dropped, text included |
| A list inside a list item | ❌ merged into its parent item |
| Tables | ❌ no table element exists in the editor |
| An image alone in a paragraph | ❌ dropped |

The editor reports no error for any of these. The article saves, and the missing piece is absent from the page.

---

#### Why Adapt the HTML Before the Tab Reaches LinkedIn?

The kit adapts the article's HTML with the browser's own DOM parser, and that parser is unusable on the editor page. LinkedIn sets a Trusted Types policy there, and `DOMParser` returns a document with no elements: a source holding 269 tags comes back as one run of text.

So the work happens one step earlier. The agent opens the HTML on `127.0.0.1`, adapts it there, and stores the result in `window.name`, which survives the navigation to LinkedIn in the same tab. The editor's own paste handling parses that HTML string correctly.

---

#### Why Keep Inline Code That LinkedIn Discards?

The editor's schema has a `code` mark, and a pasted `<code>` shows as code. After a reload the same text is plain: 40 code marks before, 0 after, with the 19 bold marks beside them intact.

Removing the inline code before the paste looks tidy and has a cost. The editor links any bare text that resembles a host name, so `make-medium.py` becomes a link to `http://make-medium.py`. With every inline code span removed first, the walk-through gained 41 link marks for its 4 real targets. With the spans left in place the editor links nothing extra, and the reload leaves plain text and 4 of 4 targets.

One exception: the `code` mark excludes every other mark, so a link whose text is inline code keeps the code and loses the link. Those spans, and only those, are unwrapped.

---

#### How Does It Compare With Medium and Substack?

All three lack tables, so the kit feeds LinkedIn the same HTML it builds for Medium, where every table is already an image. The differences:

- **Headings:** Medium has two sizes and Substack six. LinkedIn saves two, `Heading` at 24px and `Subheading` at 20px, and its paste lands every heading at the smaller one.
- **Inline code:** Substack saves it as code. LinkedIn drops the formatting and keeps the text.
- **Cover:** on Medium the first body image becomes the cover. LinkedIn has a separate cover slot that crops to 16:9.
- **Reading it back:** Medium and Substack serve the saved draft as JSON. On LinkedIn, a reload of the editor loads what was stored.

---

#### At This Point You Should Have…

- publishing-kit 0.37.1 or later in Claude Code, Codex or Antigravity, with browser automation that can run JavaScript in the page and upload a file.
- A LinkedIn account, signed in, in the browser the agent drives.
- An article already built for Medium with `make-medium.py`, its images committed and pushed.
- A 16:9 cover, the same 1200x675 image the kit makes for AWS Builder Center.

---

#### Step 1 — Build the HTML

The LinkedIn version is Medium's hosted HTML, so the build is the Medium build:

```shell
python3 make-medium.py devto-publishing-kit.md medium
```

```text
devto-publishing-kit.md: 1 tables, 0 diagrams
   USE THIS   -> medium/devto-publishing-kit-hosted.html  (paste or import; needs medium/img committed AND pushed)
   not this   -> medium/devto-publishing-kit-embed.html   (133 KB; data: URIs, Medium drops them all on paste)
```

The table becomes a PNG under `medium/img/`, and `-hosted.html` points at it by its public GitHub URL. LinkedIn fetches that URL at paste time, so the image is pushed first.

---

#### Step 2 — Adapt It on 127.0.0.1

The agent serves the repository locally, opens the hosted HTML there, and evaluates the kit's helper, `scripts/browser/linkedin-article.js`:

```js
await lia.stash()
```

```json
{"html": 11358, "carried": 12023, "first": "TL;DR: publishing-kit\npackages the whole publishing lifecycl",
 "coverDropped": "https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/publishing-kit-skill/medium/img/cover.ae4d639e.jpg",
 "imagesFigured": 1, "inlineCode": 41, "codeLinksUnwrapped": 2, "quotesSplit": 0, "nestedItemsHoisted": 0,
 "images": 1, "codeBlockLines": [2, 2, 5], "headings": {"h2": 7, "h3": 0},
 "listItems": 10, "blockquotes": 3, "tables": 0, "inkChars": 7853}
```

`stash()` makes every change the editor needs and records what it sent:

- The leading cover image is removed, because LinkedIn has its own cover slot.
- The two links around inline code are unwrapped. The other 41 inline code spans stay.
- The largest heading in the source becomes `Heading`, any smaller one `Subheading`.
- A block quote with several paragraphs is split into one quote per paragraph, and nested list items move up behind their parent, so no text is lost.
- An image alone in a paragraph is wrapped in a figure.

`inkChars` is the count of non-space characters. It is the number the final check compares.

---

#### Step 3 — Paste

The same tab opens `https://www.linkedin.com/article/new/`, the helper is evaluated again, and one synthetic paste puts the article in:

```js
await lia.paste()
```

```json
{"chars": 9462, "id": "7529254866788106240", "pasted": true, "status": "Draft - saved", "uploadsPending": 0,
 "images": [{"alt": "Table: measured", "rehosted": false, "urn": "urn:li:digitalmediaAsset:D5612AQG98xGoS3wdNw"}]}
```

The first input creates the draft, and the address becomes `/article/edit/<id>/`. `paste()` waits until each image has a LinkedIn asset id, sets the heading levels, and writes the alt text back onto each image. It refuses if the editor already holds text, so a second run cannot append the article twice.

---

#### Step 4 — Set the Title and the Cover

The title is a field of its own with a limit of 150 characters, and `lia.setTitle()` fills it.

The cover goes in the slot above the title. `lia.coverInput()` opens the upload dialog and exposes its file input, and the agent uploads the image into it. The slot crops to 16:9 from the centre: the 1376x578 dev.to cover previews as 1027x578, and the 1200x675 Builder Center cover previews whole. Upload the 16:9 one.

---

#### Step 5 — Reload, Then Check

Right after a paste the editor still shows inline code and any heading level. After a reload it holds what LinkedIn stored, so the check runs then:

```js
lia.audit()
```

```text
problems           []
title              Streamline Publishing with a Claude Code Skill
cover              true
status             Draft - saved
code blocks        3, lines 2/2/5
headings           7, all Heading
link targets       4 of 4
image              re-hosted on media.licdn.com, alt "Table: measured"
non-space chars    7853
```

`audit()` compares the stored article with what `stash()` sent: link targets missing and link targets added, code block line counts, images and their alt text, heading counts, list items, quotes, and the count of non-space characters. Any difference is a line in `problems`.

---

#### Step 6 — Publish

`Next` in the editor opens a post box that asks what the article is about, with the audience above it and a `Publish` button below. The post text is optional: `Publish` is enabled with the box empty.

The author decides to publish. For this article the audience read `Post to Anyone`, the box was left empty, and one click published it. `lia.publish()` carries that click and refuses unless the audience and post text on screen are the ones it was given.

The tab moves to the published page:

```text
https://www.linkedin.com/pulse/streamline-publishing-claude-code-skill-william-mclean-kay8c/
```

The slug is LinkedIn's own. It drops "with" and "a" from the title and adds the author's name and five characters, so the URL is read from the page. The published page holds the same 3 code blocks, 3 quotes, 10 list items and 4 link targets as the draft, and LinkedIn creates a feed post for the article at the same moment.

---

#### Step 7 — Record the Link

The URL goes into `links.txt` beside the article, and the kit's link check fetches it with the others:

```text
linkedin-article = https://www.linkedin.com/pulse/streamline-publishing-claude-code-skill-william-mclean-kay8c/
```

```shell
python3 check-links.py devto-publishing-kit.md
```

```text
  ok    links.txt medium: HTTP 200
  ok    links.txt linkedin: HTTP 200
  ok    links.txt repo: HTTP 200
  ok    links.txt substack: HTTP 200
  ok    links.txt linkedin-article: HTTP 200
```

---

#### 🔎 Tip: A 200 From /pulse/ Needs a Second Look

LinkedIn answers a `/pulse/` address that does not exist with HTTP 200. It redirects to `/top-content/?trk=article_not_found`, a page titled "Top Content on LinkedIn". The kit's link check fails any URL that lands there, so a mistyped article link cannot pass on its status code.

---

#### 🔎 Tip: Confirm the Browser Loaded the Current Build

A tab that opened the HTML on `127.0.0.1` before a rebuild can be served the older copy from its cache. The check in Step 5 then passes, because it compares the article with that same older copy. `stash()` fetches with `cache: "no-store"` and returns `first` and `inkChars`. For the walk-through the count went from 7527 to 7853 with the edit that added LinkedIn articles to it, and reading that number confirms which build is in the tab.

---

#### 🔎 Tip: Put File Names in Backticks

A file name written in a plain sentence becomes a link in the LinkedIn editor: `make-medium.py` and `dev.to` both did when pasted outside code formatting. Inside backticks the name stays text. `audit()` lists any link target the source does not hold.

---

#### Dogfooding: the Walk-Through, Published Through Its Own Kit

The article used for every step above is the kit's walk-through, "Streamline Publishing with a Claude Code Skill". It was already live on dev.to, Medium, Substack and AWS Builder Center. Adding the LinkedIn destination meant updating it to say so, rebuilding it, and sending the result through the new route.

Three of the kit's checks come from that run:

- **The character count.** A block quote drops its second paragraph and every element count stays the same. Counting non-space characters on both sides reports lost text wherever it happens.
- **Added links.** The editor adds link targets as well as dropping them, so `audit()` reports every target the source does not hold alongside every target that is missing.
- **The not-found page.** The published URL and a made-up one both answer 200, and the link check tells them apart by where the request lands.

The walk-through's own table gained a row for it, with the readings stored beside the article as evidence.

---

#### Compare and Contrast

| | Medium | Substack | LinkedIn article |
| :--- | :--- | :--- | :--- |
| How the article gets in | browser | browser | browser |
| Tables | images | images | images |
| Multi-line code | ❌ one line on import | 🟢 kept | 🟢 kept |
| Inline code | not measured | 🟢 kept | ❌ text only |
| Link around inline code | 🟢 kept | ❌ dropped; unwrap first | ❌ dropped; unwrap first |
| Heading sizes | 2 | 6 | 2 |
| Cover | first body image | not measured | separate slot, 16:9 |
| HTML adapted | in the generator | in the editor page | on `127.0.0.1`, before the editor |
| Read back from | `?format=json` | `/api/v1/drafts/<id>` | the editor after a reload |

---

#### So, Which One?

Publish to all three from the same build. LinkedIn asks for the most changes to the Medium HTML and keeps the least formatting, and the helper makes those changes before the paste. Reload before checking, and read the URL from the published page.

---

#### Summary

The goal of this article was to add LinkedIn articles to publishing-kit and publish the kit's own walk-through through it. The key to the solution was reusing the Medium HTML, adapting it on `127.0.0.1` before the tab reaches LinkedIn, and checking the article after a reload. The results were:

- 🟢 **Multi-line code kept**, 3 blocks with the same line counts.
- 🟢 **All 4 link targets kept**, with the two links around inline code unwrapped.
- 🟢 **The table image re-hosted by LinkedIn**, alt text restored.
- 🟢 **7853 non-space characters in the source and in the saved article.**
- 🟢 **Published with one click**, the URL read from the page and checked by the kit.
- ⚠️ **Two heading levels are saved**, and the paste sets every heading to the smaller one.
- ⚠️ **The cover slot crops to 16:9.**
- ⚠️ **A `/pulse/` address that does not exist answers 200.**
- ❌ **No inline code, no tables, no nested lists**, and one paragraph per block quote.

Scope: one article, pasted and published on 2026-11-19 to one LinkedIn account from a visible browser tab, with publishing-kit 0.37.1 in Claude Code on Linux. The dropped-image row comes from a second article pasted the same day, where 9 of 9 images alone in a paragraph were dropped and 9 of 9 arrived once wrapped in a figure. Editing a published article, scheduling, and a background tab were not tested. Whether a LinkedIn API can create an article was not looked up.

The strategy for publishing one markdown article to a LinkedIn article with an agent skill was validated with an incremental step by step approach.

---

#### References

* [publishing-kit | GitHub](https://github.com/xbill9/publishing-kit)
* [The LinkedIn article reference in the kit](https://github.com/xbill9/publishing-kit/blob/main/skills/publishing/references/linkedin-article.md)
* [Streamline Publishing with a Claude Code Skill | LinkedIn](https://www.linkedin.com/pulse/streamline-publishing-claude-code-skill-william-mclean-kay8c/)
* [Publishing Markdown to Substack from an Agent Skill | dev.to](https://dev.to/gde/publishing-markdown-to-substack-from-an-agent-skill-258f)
* [ProseMirror schema guide](https://prosemirror.net/docs/guide/#schema)
