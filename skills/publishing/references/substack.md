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
`links.txt` until it is published, or `SKIP` if it will not be. An article whose
`links.txt` has no `substack` line at all is treated as never sent there.

## Publishing

Not measured. Leave the draft as a draft and hand back the editor link. Before
anyone presses `Continue`, read every checkbox in what it opens, the way Medium's
dialog is read in `browser-publishing.md`: on a newsletter platform the default may
send the post to every subscriber's inbox, and an email cannot be unsent.
