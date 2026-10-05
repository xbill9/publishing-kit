# Substack, measured

Everything here was measured on 2026-10-05 by pasting this kit's own article into a
new draft on a Substack publication and reading the stored draft back. The helper
is `scripts/browser/substack-editor.js` (`window.ss`); paste it first.

## How the article gets there

**Browser automation, pasting the same `-hosted.html` that `make-medium.py`
writes.** No separate generator: Substack and Medium both lack tables, so the
table images Medium needs are the ones Substack needs. `ss.prepare()` adapts the
file in the page (below), so there is no `make-substack.py` to drift from it.

1. `python3 -m http.server 8901 --bind 127.0.0.1` from the repo root.
2. In the tab, open the hosted HTML on `127.0.0.1` and carry it and the helper in
   one `window.name`:

   ```js
   const html = await (await fetch(location.href)).text();
   const js = await (await fetch('/skills/publishing/scripts/browser/substack-editor.js')).text();
   window.name = JSON.stringify({html, js});
   ```

3. Navigate the same tab to `https://<pub>.substack.com/publish/post?type=newsletter`.
   MEASURED 2026-10-05: that URL **creates a draft** and redirects to
   `/publish/post/<id>`, so open it once per article. `window.name` arrived intact
   (20,066 characters).
4. In the editor: `const p = JSON.parse(window.name); (0,eval)(p.js);` then
   `ss.prepare(p.html)`, `await ss.paste()`, `ss.setTitle(title, description)`,
   `await ss.audit()`. `eval` is allowed on the editor page (MEASURED 2026-10-05).

All of it ran in a hidden tab (`document.visibilityState === "hidden"`).

## Audit the saved draft, not the editor DOM

The editor's page can read the draft as Substack stored it:
`GET /api/v1/drafts/<id>` (same origin, the session's cookies) returns
`draft_title`, `draft_subtitle` and `draft_body`, a ProseMirror document as a JSON
string. `ss.audit()` waits for the autosave and counts that document: headings by
level, code blocks with their line counts, images (re-hosted or not, alt, width),
the set of link targets, and the first and last text. Compare it with the source.
The endpoint is the editor's own and undocumented; this kit uses it only to read
back.

What the paste produced, MEASURED 2026-10-05, against the hosted HTML it came from:

| Source | Saved draft |
| --- | --- |
| 4 `<pre>` blocks, 2/2/1/4 lines | 4 `code_block`, 2/2/1/4 lines, same character counts |
| 2 `<img>` on `raw.githubusercontent.com` | 2 `image2`, both re-hosted on `substack-post-media.s3.amazonaws.com`, `alt` kept |
| 4 distinct link targets | 4, once `prepare()` had run (2 without it, below) |
| pandoc-wrapped paragraphs | 0 of 39 paragraphs hold a newline |

**Multi-line code survives as text here**, which Medium's importer does not
allow. **Alt text survives the paste**, which Medium's paste does not.

## What the editor cannot hold

Read from the editor's own schema (`document.querySelector('.ProseMirror').editor.schema`),
MEASURED 2026-10-05:

- **There is no table node.** Tables must arrive as images; the hosted HTML
  already renders them that way.
- **The `code` mark has `excludes: "_"`**: inline code carries no other mark. A
  link whose text is inline code (`<a><code>path</code></a>`, which pandoc writes
  for `` [`path`](url) ``) **loses the link and keeps the code**, with no error.
  Two of two such links vanished in the first paste while the four plain links
  beside them survived, so the test could produce a positive. `ss.prepare()`
  unwraps `<code>` inside `<a>`; the second paste kept all four targets.
- **A ` ```text ` fence becomes a maths block.** MEASURED 2026-10-05: of nine
  pasted `<pre>` blocks, the six classed `shell`, `js` and `json` saved as
  `code_block`, and the three classed `text` saved as `latex_block`, the
  editor's LaTeX element. `ss.prepare()` removes the classes from `<pre>` and
  `<pre><code>` (a saved `code_block` keeps no language anyway); the re-paste
  saved nine `code_block` with matching line counts and no `latex_block`.
  `ss.audit()` counts `latex_block` among the types, so a stray one shows up.
- A `gitgist` node exists. Whether a pasted gist URL becomes one is not measured.

## Headings: Substack has six sizes

`make-medium.py` demotes sections to `<h4>` because Medium has two heading sizes.
Substack renders `h1`–`h5` at 38, 30.9, 26.1, 21.4 and 15.8 px against 19 px body
text (MEASURED 2026-10-05, computed styles in the editor), so an `h4` section is
barely larger than a paragraph. `ss.prepare()` turns every `h4` into an `h3`;
`ss.prepare(html, {sectionHeading: "h2"})` picks another level.

## Title and subtitle

The post's title and subtitle are `<textarea>` elements with placeholders `Title`
and `Add a subtitle…`. The page also holds an `<input>` "Add a title..." and a
`<textarea>` "Add a description...": those are the SEO fields, a separate pair.
`ss.setTitle()` sets the first pair through the native value setter and fires
`input`; MEASURED 2026-10-05, both came back in `draft_title` / `draft_subtitle`.
The house subtitle is the front matter's `description`.

**A subtitle over 255 characters stops the whole draft saving.** MEASURED
2026-10-05: with a 284-character description, the editor showed "Draft not saved
/ Subtitle is too long", and the stored draft kept an empty title and a 74-character
empty body while the editor showed the full paste. Set one at a time and read
back: 255 saved, 256 and 257 did not, and 241 and 248 to 254 saved, body
included. The "Subtitle is too long" banner stayed on the page after the later
saves succeeded, so judge by `ss.audit()`, never by the banner. `ss.setTitle()`
refuses a subtitle over 255; cut the description at a sentence.

## Replacing the body

`ss.clear(<id>)` calls the editor's own `clearContent` and takes the draft id so
it cannot clear the wrong draft. MEASURED 2026-10-05: the body went to 0
characters, the title and subtitle stayed, and a fresh paste followed cleanly.
`ss.paste()` refuses on a non-empty editor, as every helper in this kit does.

## Links

MEASURED 2026-10-05 with `check-links.py`'s fetch: a published post
(`<pub>.substack.com/p/<slug>`) and a profile (`substack.com/@<handle>`) answered
200; a slug that does not exist answered 404. No bot wall, so no exemption like
dev.to's and Medium's. A draft has no public URL: put `substack = PENDING` in
`links.txt` until it is published, then the URL `ss.published()` returns, or `SKIP` if it will not be. An article whose
`links.txt` has no `substack` line at all is treated as never sent there.

## Publishing

MEASURED 2026-10-05, publishing this kit's article from a hidden tab. Use
`ss.openPublish()`, `ss.publish({...})` and `ss.published(<id>)`.

- **`Continue` opens a `Publish` modal on the same URL**, with no navigation.
  Its defaults: audience **Everyone**, comments **Everyone**, **"Send via email
  and the Substack app" ON**, scheduling off, and the button reads **"Send to
  everyone now"**. Left alone, publishing emails every subscriber, and the email
  cannot be unsent. Ask the author which they want before the click;
  `ss.publish()` refuses without an explicit `email: true|false` and on any
  setting that does not match what was asked for.
- **A second modal holds the publish.** After "Send to everyone now", the first
  modal shows `Publishing...` and nothing happens for as long as you wait (35 s
  measured) while a separate `[role=dialog]`, "Add subscribe buttons to your
  post", waits for `Add subscribe buttons` or `Publish without buttons`. A read
  of the first dialog alone shows only the spinner. `ss.publish()` answers it,
  without buttons unless `{subscribeButtons: true}`.
- **The tab then moves** to `/publish/posts/detail/<id>/share-center`, where a
  "Stats are better in the app" dialog opens. The confirmation is the post in
  `GET /api/v1/post_management/published`, with `post_date` and `email_sent_at`
  set; `ss.published()` reads it.
- **The slug is cut short.** "Streamline Publishing with a Claude Code Skill"
  published as `/p/streamline-publishing-with-a-claude`, so take the URL from
  `ss.published()`, never from the title. Whether the slug can be set before
  publishing is not measured.
- **The public page matches the draft.** The served post body held 4 `<pre>`,
  7 `<h3>`, 2 images and all 4 article link targets, and each heading gained an
  anchor at `/i/<id>/<heading-slug>`. The raw page holds the body markup more
  than once (8 `<pre>`, 16 `<h3>` in the whole document), so count inside
  `class="body markup"`.

**`ss.publish()` has run end to end.** MEASURED 2026-10-05 on a second post:
`openPublish()` read the settings, `publish({email: true, audience: "everyone",
comments: "everyone", scheduled: false})` returned `clicked: "Send to everyone
now"` and `answered: "Publish without buttons"`, and `published()` returned the
post with `email_sent_at` set. Its first read of the dialog picked the
social-preview card as the send button, because that card is a `<button>` whose
text starts with the post title, and this title starts with "Publishing"; the
helper now accepts single-line labels only. Read `openPublish()`'s `button`
before calling `publish()`.

## Updating a published post

MEASURED 2026-10-05 on both posts, done step by step in a hidden tab:

- `/publish/post/<id>` opens the published post in the same editor, and edits
  save to a draft copy (`draft_updated_at` moves; the live page does not).
  `ss.clear(<id>)`, `ss.prepare()`, `ss.paste()` and `ss.audit()` work there
  unchanged.
- Once the draft differs from the live post, the editor's button reads
  **`Update`** where a new draft shows `Continue`.
- `Update` opens the same `Publish` modal **with no Delivery section and no
  email checkbox**, and its button reads **`Update now`**. After it, both posts
  kept their original `email_sent_at`, so an update sends no second email. No
  subscribe-buttons modal followed.
- The tab moves to `/publish/posts/detail/<id>/share-center?alreadyPublished=true`
  immediately, which ends any script still running in the page.
- The live page served the new body at once: the new paragraph, the new table
  image (`_1146x436.png` against `_1146x382.png` before), and on the other post
  the new cover. Substack re-hosts an image under a new name on every paste, so
  compare the re-hosted bytes against the local file. The new cover
  differed from the local file by 0.0 mean per pixel, the old one by 18.71.
- **A changed image must reach the CDN before the paste.** Substack fetches
  `raw.githubusercontent.com/.../main/...` at paste time; after a push, that URL
  served the previous bytes for several minutes (`check-links.py` failed it while
  `--pinned` passed). Paste once `check-links.py` without `--pinned` passes.

`openPublish()` and `publish({update: true})` carry this route; the helper
refuses an update without `update: true`, and clicks `Update now` after
returning. The two updates above were run step by step, before those lines were
written.

**Slugs seen so far are cut to about 35 characters on a word boundary:**
`streamline-publishing-with-a-claude` and `publishing-markdown-to-substack-from`.
