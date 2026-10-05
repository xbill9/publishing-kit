---
title: "Publishing Markdown to Substack from an Agent Skill"
published: false
description: "Substack has no publishing API, its editor has no tables, and a link around inline code is dropped on paste. A step by step walk-through of the Substack destination in publishing-kit: what the editor keeps, what it drops, and how an agent publishes to it and reads the result back."
tags: substack, writing, devtools, ai
cover_image: https://raw.githubusercontent.com/xbill9/publishing-kit/main/articles/substack-destination/cover.325bdb37.jpg
---

This article provides a step by step guide to publishing a markdown article to Substack with publishing-kit, an agent skill for Claude Code, Codex and Antigravity. Substack is the kit's fifth destination, after dev.to, Medium, AWS Builder Center and LinkedIn, and every output below comes from publishing the kit's own walk-through to a Substack publication.

https://github.com/xbill9/publishing-kit

**One markdown file goes in. A Substack post comes out, with every code block, image and link checked in the draft Substack saved before it goes live.**

---

#### What Is the Problem?

Substack has no publishing API. A post goes in through its web editor, and that editor decides what survives.

Pasting HTML into it, then reading back the draft Substack stored, gives this:

| Content | In the saved draft |
| :--- | :--- |
| Multi-line code blocks | 🟢 kept, same line and character counts |
| Images on public URLs | 🟢 fetched and re-hosted by Substack, alt text kept |
| Plain links | 🟢 kept |
| Tables | ❌ no table element exists in the editor |
| A link whose text is inline code | ❌ the link is dropped, the code is kept |
| A code block marked `text` | ❌ saved as a maths (LaTeX) block |
| Section headings | ⚠️ kept at the level pasted, in six distinct sizes |

None of the failures produces an error. The table disappears, or a link becomes plain monospace text, and the editor saves it.

---

#### Why Does the Link Disappear?

Substack's editor is built on ProseMirror, and its schema lists every element and mark a post can hold. The `code` mark is declared with `excludes: "_"`, which means inline code can carry no other mark: no bold, no italic, no link.

So `` [`skills/publishing/SKILL.md`](https://github.com/xbill9/publishing-kit/blob/main/skills/publishing/SKILL.md) `` arrives as `<a><code>skills/publishing/SKILL.md</code></a>`, and the editor keeps the code and discards the link. The kit's walk-through has two links written that way, and pasted as-is, its saved draft holds 2 link targets out of 4.

The fix is to take the `<code>` out of the anchor before pasting. The link survives as plain text, which keeps the reader's way to the page.

---

#### How Does Substack Compare With Medium?

Both lack tables, so the kit feeds Substack the same HTML it builds for Medium, where every table is already an image. After that they part ways:

- **Code:** Medium's importer flattens multi-line code to one line. Substack keeps it as a real code block.
- **Alt text:** Medium's editor blanks it on paste. Substack keeps it.
- **Headings:** Medium has two heading sizes, so the kit demotes sections to `<h4>` for it. Substack has six, and renders `<h4>` at 21.375px against 19px body text, so a section heading barely stands out.
- **Publishing:** both default to notifying subscribers. On Substack that is an email to every subscriber and a push to the Substack app.

---

#### At This Point You Should Have…

- publishing-kit 0.32.0 or later in Claude Code, Codex or Antigravity, with browser automation that can run JavaScript in the page.
- A Substack publication, signed in, in the browser the agent drives.
- An article already built for Medium with `make-medium.py`, its images committed and pushed.

---

#### Step 1 — Build the HTML

The Substack version is Medium's hosted HTML, so the build is the Medium build:

```shell
python3 make-medium.py devto-substack-destination.md medium --cover=cover.325bdb37.jpg
```

```text
devto-substack-destination.md: 2 tables, 0 diagrams
   USE THIS   -> medium/devto-substack-destination-hosted.html  (paste or import; needs medium/img committed AND pushed)
   not this   -> medium/devto-substack-destination-embed.html   (211 KB; data: URIs, Medium drops them all on paste)
   Medium never fills its Title field from pasted content -- set the title separately.
```

Tables and box-drawing diagrams become PNGs under `medium/img/`, and `-hosted.html` points at them by their public GitHub URL. Substack fetches each one and re-hosts it on its own image server.

---

#### Step 2 — Carry the Page Into the Editor

The editor page's content security policy blocks a `fetch` to the local machine, so the HTML travels in `window.name`, which survives a navigation in the same tab. The agent serves the repository on `127.0.0.1`, opens the hosted HTML there, and stores it and the kit's Substack helper together:

```js
const html = await (await fetch(location.href)).text();
const js = await (await fetch('/skills/publishing/scripts/browser/substack-editor.js')).text();
window.name = JSON.stringify({html, js});
```

Then the same tab opens `https://<pub>.substack.com/publish/post?type=newsletter`. That URL creates a new draft and redirects to `/publish/post/<id>`, and the payload arrives intact: 20,066 characters of HTML in this run.

---

#### Step 3 — Prepare and Paste

In the editor, the helper loads from the payload and adapts the HTML before pasting it:

```js
const p = JSON.parse(window.name); (0, eval)(p.js);
ss.prepare(p.html)
```

```json
{"anchors": 6, "codeLinksUnwrapped": 2, "html": 11557, "images": 2, "pres": 4}
```

`prepare()` removes the title block, because Title and subtitle are separate fields, unwraps the two links around inline code, and promotes Medium's `<h4>` sections to `<h3>`. It also clears the language class from every `<pre>`: pasted as-is, a block fenced as ` ```text ` is saved as `latex_block`, Substack's maths element, while `shell`, `js` and `json` blocks are saved as code. Substack's code blocks store no language, so nothing is lost. Then a single synthetic paste:

```js
await ss.paste()
```

```json
{"chars": 9020, "pasted": true}
```

`paste()` refuses if the editor already holds text, so a second run cannot append the article twice. Everything here works in a background tab, where typed keystrokes are unreliable.

---

#### Step 4 — Read Back the Saved Draft

The editor's DOM shows what is on screen. What gets published is the draft Substack stored, and the editor page can read it as JSON from `/api/v1/drafts/<id>`. `ss.audit()` waits for the autosave and counts that document:

```text
code_block         4, lines 2/2/1/4
image2             2, both substack-post-media.s3.amazonaws.com, alt kept
heading            7 (h3 7)
link targets       https://github.com/xbill9/publishing-kit
                   https://github.com/xbill9/publishing-kit/blob/main/skills/publishing/SKILL.md
                   https://github.com/xbill9/publishing-kit/tree/main/articles/publishing-kit-skill
                   https://claude.com/claude-code
```

Every count matches the HTML that went in: 4 code blocks with the same line counts, 2 images, 4 link targets.

---

#### Step 5 — Set the Title and Subtitle

The editor page holds two pairs of title fields. The post's own are textareas with the placeholders `Title` and `Add a subtitle…`; an `Add a title...` input and an `Add a description...` textarea belong to the SEO settings. `ss.setTitle()` fills the first pair, using the front matter's `title` and `description`, and the audit confirms both reached the saved draft.

The subtitle has a limit of 255 characters, and going over it stops the whole draft saving, body included, while the editor still shows everything. A "Subtitle is too long" banner appears, and stays on the page even after a later save succeeds, so the saved draft is the only reliable signal. `ss.setTitle()` refuses a subtitle over 255; this article's description is longer, so its Substack subtitle ends after the second sentence.

---

#### Step 6 — Publish

`Continue` opens a Publish dialog on the same page. `ss.openPublish()` reads its settings, which by default are:

```text
audience           everyone
comments           everyone
"Send via email and the Substack app"   checked
"Schedule time to email and publish"    unchecked
button             "Send to everyone now"
```

Left alone, publishing emails every subscriber. An email cannot be recalled, so the author decides before the click. For this post the author chose to send it, and the settings were checked once more inside the same script that clicked "Send to everyone now".

A second dialog follows, "Add subscribe buttons to your post", and the publish waits at `Publishing...` until it is answered; this post went out with `Publish without buttons`. The helper's `ss.publish()` carries that whole route: it refuses unless it is told whether to send the email, refuses on any setting that differs from what it was told, and answers the second dialog:

```js
await ss.publish({email: true, audience: "everyone"})
```

Then `ss.published()` reads the post back from the publication's list:

```json
{"audience": "everyone", "email_sent_at": "2026-10-05T17:19:32.552Z", "id": 218966232,
 "post_date": "2026-10-05T17:19:32.878Z", "slug": "streamline-publishing-with-a-claude",
 "url": "https://xbill9.substack.com/p/streamline-publishing-with-a-claude"}
```

The slug is shorter than the title, so the URL comes from this response, never from the title.

---

#### Step 7 — Add the Link to the Announcements

The URL goes into `links.txt` beside the article, which feeds the LinkedIn, Slack and Google Chat posts:

```text
substack   = https://xbill9.substack.com/p/streamline-publishing-with-a-claude
```

```shell
python3 make-slack.py devto-publishing-kit.md
```

```text
  ok    Builder Center: HTTP 200
  WARN  Medium: HTTP 403 to a browser UA (dev.to/Medium bot wall, not a broken link)
  ok    Substack: HTTP 200
  ok    Dev.to (aws-builders): HTTP 200
  ok    LinkedIn: HTTP 200
  ok    no markdown left; Slack renders none of it

0 fail, 1 warn
```

Substack answers a published post with 200 and a missing slug with 404, to a client with no cookies, so its links are checked like any other. A `substack = PENDING` line fails the run until the post is live.

---

#### 🔎 Tip: Count Inside the Post Body

The public page carries the post's markup more than once: the served HTML for this post holds 8 `<pre>` and 16 `<h3>`. Inside the `class="body markup"` element it holds 4 and 7, matching the draft. Substack also adds an anchor link to every heading, at `/i/<id>/<heading-slug>`.

---

#### 🔎 Tip: Read the Saved Draft, Not the Screen

The editor renders what it holds, and a dropped link still looks like code on screen. The JSON document behind the draft lists every link target, so a missing one is a line that is absent from the list.

---

#### Compare and Contrast

| | Medium | Substack |
| :--- | :--- | :--- |
| Publishing API | ❌ none | ❌ none |
| Tables | images | images |
| Multi-line code | ❌ one line on import | 🟢 kept 🥇 |
| Image alt text on paste | ❌ blanked | 🟢 kept 🥇 |
| Link around inline code | 🟢 kept | ❌ dropped; unwrap first |
| Heading sizes | 2 | 6 |
| Read back from | `?format=json` | `/api/v1/drafts/<id>` |
| Default on publish | notify subscribers | email every subscriber |

---

#### So, Which One?

Publish to both from the same build. Substack keeps more of the article than Medium does, code and alt text included, and asks for only two changes to the Medium HTML. Read the saved draft before publishing, and decide on the subscriber email before opening the Publish dialog.

---

#### Summary

The goal of this article was to add Substack to publishing-kit and publish an article to it. The key to the solution was reusing the Medium HTML, adapting it in the page, and checking the draft Substack stored. The results were:

- 🟢 **Multi-line code kept**, 4 blocks with the same line counts.
- 🟢 **Images re-hosted by Substack**, alt text kept.
- 🟢 **All 4 link targets kept**, once the links around inline code were unwrapped.
- 🟢 **Plain-text code blocks kept as code**, once their language class was cleared.
- 🟢 **The URL read back after publishing**, and checked by the announcement scripts.
- ⚠️ **Publishing emails every subscriber by default**, and waits on a second dialog.
- ⚠️ **A subtitle over 255 characters stops the draft saving**, body included.
- ❌ **No tables and no API**: tables arrive as images, and the post goes in through the browser.

Scope: one article, published on 2026-10-05 to one Substack publication from a background browser tab, with publishing-kit 0.32.0 in Claude Code on Linux. Element and size findings come from that editor's schema and styles on that date.

The strategy for publishing one markdown article to Substack with an agent skill was validated with an incremental step by step approach.

---

#### References

* [publishing-kit | GitHub](https://github.com/xbill9/publishing-kit)
* [Substack](https://substack.com)
* [ProseMirror schema guide](https://prosemirror.net/docs/guide/#schema)
* [Write Markdown Once, Publish It Everywhere | dev.to](https://dev.to/gde/write-markdown-once-publish-it-everywhere-devto-medium-aws-builder-center-and-linkedin-np4)
