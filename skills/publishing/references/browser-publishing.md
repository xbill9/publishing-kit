# Driving the editors in a browser

> **First: is there an API?** dev.to has one, and this skill wraps it in
> `scripts/publish-devto.py`. A whole browser flow was once built for dev.to while
> an API wrapper sat unused. Use the bundled script rather than opening a tab. The
> browser is the fallback for destinations with no API — currently Medium and AWS
> Builder Center.


Measured 2026-08-30 while putting one article into Medium and AWS Builder Center.
Every item below cost real time. The theme: **these editors fail silently and
plausibly** — you get a clean-looking draft that is missing something, so the only
defence is to verify the artifact, not the return value.

## The mandatory check after any paste

Before calling a draft done, confirm **each of these separately**. Do not infer one
from another; they fail independently.

1. **Images.** Count them against the source. A missing image leaves ordinary
   whitespace, not a placeholder.
2. **Title field.** Separate from the body on every platform. Usually empty.
3. **Code blocks.** Multi-line, or flattened to one line?
4. **Tables.** Present as images (Medium) or as real tables (Builder Center)?
5. **The last paragraph.** Confirms nothing was truncated.

A screenshot at the top of the document proves none of this. Scroll the whole thing.

## The clipboard is shared — do not use it

`ctrl+A` / `ctrl+C` to lift content from a source page **overwrites the user's system
clipboard**, and this user works in parallel browser tabs on other articles. It
destroyed a clipboard mid-session.

Inject through the JS bridge instead. It never touches the clipboard:

**Pick the editor by what it is, not by its position.** MEASURED 2026-09-08 on
Medium: `[contenteditable="true"]` returns two nodes, and the last is a hidden
100x100 div parked at `x=-9999`. `eds[eds.length - 1]` — which this file used to
recommend — pastes into that and reports success, because `dispatchEvent` returns
the same `false` either way. Select the real editor, and assert it is on screen:

```js
const md = new TextDecoder().decode(Uint8Array.from(atob(b64), c => c.charCodeAt(0)));
const ed = document.querySelector('.postArticle-content[contenteditable="true"]');
if (!ed || ed.getBoundingClientRect().width < 200) throw new Error("not the body editor");
ed.focus();
const dt = new DataTransfer();
dt.setData('text/plain', md);
ed.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
```

**Base64-encode the payload** and decode it in the page. It sidesteps every escaping
problem with backticks, `${`, quotes and newlines in one move.

`dispatchEvent` returns **`false`**. That is `preventDefault`, not refusal. Verify by
screenshot, never by return value.

## The extension cannot open `file://`

`navigate` rejects local files outright. Serve the artifact over HTTP instead — for
this repo, `docs/` is on GitHub Pages, so committing and pushing makes it reachable.
That push is needed anyway for the hosted variant's images.

## Hard-wrapped markdown breaks in a contenteditable

Markdown wrapped at 80 columns pastes into Builder Center's editor with the wraps
**preserved as line breaks**, shredding every paragraph. Unwrap paragraphs to one
long line each before pasting, while leaving these on their own lines: blank lines,
headings, table rows (`|`), list items, and everything inside fenced code blocks.

Longest line after unwrapping runs ~650 chars. That is correct, not a problem.

## Medium: the editor ignores DOM edits

MEASURED 2026-08-30, twice, at the cost of a whole cleanup pass that silently
undid itself.

**Anything you change in the DOM is discarded.** `element.remove()`,
`execCommand("delete")`, and a caret placed with the Selection API followed by a
synthetic key all *appear* to work — the DOM updates, the audit reads clean — and
then the change is gone on reload, because Medium's model never saw it. The first
attempt at this was abandoned when a "Leave site?" dialog appeared, which is the
only signal you get.

**What works is a real click plus real keys.** Compute the element's viewport rect
with a `Range`, click it with the mouse tool, then send keystrokes. Then **reload
and re-audit** — the DOM immediately after an edit is not evidence, only the DOM
after a reload is.

- **Deleting an empty block:** click into it, `Backspace` twice — the first strips
  the block format, the second removes the now-empty paragraph. Work bottom-up so
  earlier positions do not shift.
  **Two Backspaces do not mean one block.** MEASURED 2026-09-09: on a paste with
  3 empty blockquotes around 1 real one, the first click-plus-two-Backspaces took
  the count 4 -> 2, removing *both* trailing empties. Repeating it on the last
  empty took 2 -> 0 and ate the **real** blockquote too, stripping its format and
  merging its text into the preceding paragraph — `its place:IMPORTANT: check…`
  with no break. Nothing was lost, but the fix is a second edit. **Re-count after
  every Backspace pair rather than assuming one pair removes one block**, and stop
  as soon as the empties are gone.
- **Re-splitting a paragraph the Backspace merged:** click at the boundary, assert
  the caret with `getSelection()` (`before` should end with the first paragraph,
  `after` be empty at a node edge), then `Return`. To restore blockquote format,
  triple-click the paragraph and click the `"` button in the floating toolbar.
  Both survive a reload.
- **Changing one word:** get the character's rect from a `Range`, click at its
  right edge, confirm the caret with `getSelection().anchorOffset` and the
  surrounding text, then type. Do not double-click a one- or two-letter word — at
  that size the hit lands on the neighbouring space and selects that instead.

### Pasting inserts empty blockquotes

A paste that contains a blockquote arrives with **empty blockquotes wrapped around
the real one** — 3 empties around 1 real, in the measured case. These show as blank
quoted gaps. Count blockquotes against the source and delete the empties with the
click-and-Backspace route above.

### Pasting inserts empty code blocks, and they DO render

MEASURED 2026-09-08. A 24-code-block article pasted as 42 blocks, 18 of them
empty. **This file previously said empty code blocks do not render publicly. They
do** — 66px grey boxes, confirmed on the draft's own `/p/<id>` view, which renders
a draft as a story without publishing it and is the cheapest way to settle any
"does this show up?" question here.

The trigger is pandoc's syntax highlighting: every block it wrapped in
`div.sourceCode` with per-line `<span>`s got a trailing empty block, and the six
plain blocks in the same article got none. `make-medium.py` now passes
`--no-highlight`, which costs nothing because Medium discards that markup and
re-runs its own language detection on paste — the published story is syntax
coloured either way.

**The general lesson is the one this kit keeps relearning: check the rendered
view, not the editor.** The editor decorates an empty code block with an
`Auto (TypeScript)` label, so its `innerText` is not empty and a naive
"is it blank?" test in the editor misses all 18.

### Audit a Medium draft from `?format=json`, never from the DOM

MEASURED 2026-09-22, after three wrong verdicts in one session. Neither view in
the browser tells you what Medium stored:

- **The editor DOM lies.** A 31,472-character paste left a document with 28
  headings and 6 figures in the DOM, `Saved` in the header — and 39 blocks with
  no images in the model. The kit already says Medium discards DOM edits; it
  discards a paste it did not commit the same way, and the audit reads clean.
- **The story view (`/p/<id>`) windows its DOM.** The same draft reported 17
  headings on one pass and 29 on another, scrolling the whole document each
  time. Counts off it are a lower bound, not a count.

The model itself is one fetch, same-origin from any Medium page:

```js
const r = await fetch(`https://medium.com/p/${id}?format=json`, {credentials:"include", cache:"no-store"});
const j = JSON.parse((await r.text()).replace(/^[^{]*/, ""));   // strip the anti-JSON prefix
const ps = j.payload.value.content.bodyModel.paragraphs;
({n: ps.length, headings: ps.filter(p=>p.type===13).length, images: ps.filter(p=>p.type===4).length})
```

Paragraph `type`: **1** text, **3** title, **4** image, **8** code, **9** list
item, **13** heading. Check the count, the image count and the last block's text
against the source before believing a paste landed.

### `Saved` is not the end of the commit — poll the model until it stops growing

MEASURED 2026-09-22. Medium fills the body model **progressively** after a large
paste, and the header reads `DraftSaved` while it is still going. On a 137-block
document the model read **48 blocks and 2 of 6 images** at the moment the header
said `Saved`, and reached 137 blocks and 6 images about a minute later.

So `Saved` is a starting gun, not a finish line. After a paste, poll
`?format=json` until the paragraph count is stable across three reads, and only
then navigate, reload or audit. Reloading early is what silently truncates a
draft: an earlier run in this session lost its whole `References` section that
way and, on a second attempt, cut a 137-block draft down to 39 permanently.

### Do not repair a draft by re-pasting over a selection

MEASURED 2026-09-22. Selecting the body (from the empty `<p>` after the title to
the last `.graf`) and pasting the whole document over it **rendered correctly in
the editor and never reached the model** — the draft was left at 39 blocks with
its images gone, and the damage does not undo: an empty payload pasted over a
selection is a no-op, and the tab had no keyboard focus for `Ctrl+Z`.

Appending to the end does not work either. The caret lands inside the final
`<li>`, so the paste is taken as list continuation: an `<h4>` is flattened into
the preceding bullet's text (`…what references themReferences`) and the new
items join that list.

**Build a fresh story instead** (`medium.com/new-story`): paste the title as
`text/plain` into `h3.graf--title`, paste the body as `text/html` into the empty
`p.graf--p`, wait out the progressive commit, and verify from `?format=json`.
That route produced a complete 137-block, 28-heading, 6-image draft. The old
draft has to be deleted by hand, which is the cost of it being the reliable one.

### Re-pasting over an existing draft

Import cannot update a draft, but paste can, and it keeps the id and the link:

1. Click in the body, then `ctrl+a`. It selects **the title as well as the body** —
   Medium is one editable. Read the selection back after ~1 s; read it immediately
   and it comes back empty even when it worked.
2. `Delete`. Assert the article is empty (`innerText` down to the `Tell your story…`
   placeholder) before going further.
3. Type the title, press `Return`. This re-creates the title block the `ctrl+a` ate
   and leaves the caret in the body.
4. Dispatch the paste with `text/html` only.
5. Audit: landmark counts (opening, summary heading, closing line = 1 each), image
   count and that each `src` is re-hosted (`cdn-images-1.medium.com/max/800/0*` in the
   2026-09-09 run, `miro.medium.com` elsewhere — match on the `0*` segment, not the
   host), heading level,
   multi-line code blocks, then **reload and audit again**.

## Medium

- Paste `-hosted.html`, never `-embed.html`. See `medium.md` — the embed variant
  loses every image.
- Type the title by hand; no paste route fills it.
- The editor autosaves and shows `Saved`; the URL changes to `/p/<id>/edit` on the
  first save. That id is the draft link.
- **Importing cannot update an existing draft.** It always creates a new one, so a
  revised article means a new draft and deleting the old one by hand.

### Medium's publish dialog defaults to Paywall AND Notify

MEASURED 2026-08-30. Both checkboxes come up **checked** once the dialog hydrates —
the first screenshot after the click shows them unchecked, which is the pre-hydration
state and a lie. Left alone, publishing paywalls the story and emails every
subscriber. Read them back with JS and set them deliberately:

```js
[...document.querySelectorAll('input[type=checkbox]')].map(c => ({
  label: (c.closest('label') || c.parentElement.parentElement).innerText.split('\n')[0],
  checked: c.checked }))
```

The subscriber email cannot be un-sent; the paywall can be changed afterwards.

**Typing when the topic input has lost focus toggles those checkboxes.** The field
drops focus after each accepted topic, and a stray `type` then lands on the page —
a space bar toggles whichever checkbox is focused, which is how a story silently
became paywalled here. Assert `document.activeElement.placeholder` starts with
`Add` before every `type`, and re-read the checkbox states before clicking Publish.

Topics: type the term, wait, press `Return` — the chip appears and the placeholder
changes from `Add a topic...` to `Add more topics...`, which is the reliable signal
it was accepted. Not every term resolves (`Llm` did not); check the chips rather
than assuming.

### After publishing, the story moves to a subdomain

The published URL is `<handle>.medium.com/<slug>-<id>`, a different origin from
`medium.com` — so the extension's per-domain permissions may not cover it, and
`screenshot` / `javascript_tool` start failing there while `get_page_text` still
works. Medium also answers `curl` with **403**, so verify the published article
with `get_page_text` in the browser, not from the shell.

The `<handle>` is Medium's, not the dev.to or GitHub username, and they need not
match — the 2026-09-09 run published as `xbill999.medium.com` from an account
whose dev.to handle is `xbill`. Do not construct the published URL by hand; read
it back from the tab.

**Confirmed 2026-09-09, and worth naming as a success signal:** the screenshot
immediately after clicking Publish failed with `Permission denied for this action
on this domain`. That error *is* the confirmation — it means the tab already moved
to the subdomain. Call `tabs_context_mcp` for the new URL rather than treating it
as a failed publish.

## AWS Builder Center: check you are signed in first

There is no API, so a signed-out session blocks **everything** — a draft cannot even
be read. The sign-in is a Builder ID / Google / GitHub modal, so it is not
automatable and not something to work around: stop and tell the user the session
expired, with the draft URL, rather than burning turns on it. Published articles
stay readable while signed out, so verifying a *published* piece still works.

## AWS Builder Center

- New article: **"+" in the top bar → Article.** Never open an existing draft's
  preview to edit — that overwrites the other piece. This matters more than it
  sounds: the user often has another draft in flight in a parallel tab.
- The page loads as skeleton placeholders first. Wait for it, or clicks land on
  nothing.
- Title and Description are ordinary inputs; click and type. Body is the
  `contenteditable` — use the JS bridge above.
- Tables and multi-line code both render natively. No image conversion.
- **The cover uploads headlessly. Do not hand it back.** The widget looks like
  drag-and-drop only, but there is a real `input[type=file]` behind the "Upload
  image" button (`accept=".jpg, .jpeg, .png, .webp"`). Locate it with `find`, then
  use `file_upload` with its ref:

  ```
  find      → "cover image file upload input"  → ref_NNN
  file_upload  paths=["…/builder-cover.jpg"]  ref=ref_NNN
  ```

  A repo path works; the file does not need copying into a shared folder. After the
  upload the ref is **destroyed** — the widget swaps to a preview card showing the
  filename and size — so a following `scroll_to` on that ref errors. That error is
  success, not failure; screenshot instead.

  Never click a file-upload button directly: that opens a native picker you cannot
  see or dismiss.
- **Tags are a fixed AWS taxonomy, not free text.** Typing `jax` returns nothing at
  all, which reads like a broken control. Search AWS terms: `EC2` → `amazon-ec2`,
  `generative` → `generative-ai`, `machine` → `machine-learning` / `virtual-machine`.
  Five maximum. Clicking the search box's clear-X reopens the full tag list; press
  Escape and click elsewhere to dismiss it.
- It autosaves — "Saved to your drafts", no save button.

### Editing a Builder Center draft in place: `scripts/browser/builder-editor.js`

MEASURED 2026-09-15, repairing a live draft without re-pasting it. Paste the file
into the editor page once; it defines `window.bc`. Every mutating helper checks
its precondition inside the same script and returns `{refused: …}` instead of
acting, which is a real guard — unlike an assertion inside a `browser_batch`.

- **Typing can silently go nowhere.** The editor tab reported
  `document.visibilityState === "hidden"`; `computer type` returned success and no
  text landed in the body, the title, the description or any input, and
  screenshots timed out. A synthetic `paste` over a `Range` selection still
  updated the model and autosaved. So `bc.replaceText` and `bc.replaceBlock` edit
  by selecting and pasting, never by typing. After any typed edit, read the text
  back before believing it.
- **Swapping a link:** `bc.replaceBlock("Old label | Site", "[New label](https://…)")`.
  The selection starts outside the anchor, so the paste does not inherit the old
  href, and the paste handler turns the markdown into a real link.
- **Code blocks are non-editable widgets.** `bc.replaceInCodeBlock(old, new)` opens
  the block's "Code block options" → Edit dialog and calls `setValue` on the Ace
  editor inside it, then Save. A plain `.click()` on the options button did not open
  the menu; the pointer/mouse event sequence in `bc.press` did.
- **Markdown images are dropped on save**, and Insert image rejects external URLs
  with "Invalid image URL". Upload each image through the dialog:
  `bc.caretBefore("<paragraph that follows the image>")`, send real keys
  `Return Up`, confirm with `bc.caretSlot(prefix)`, then `bc.openInsertImage(prefix)`.
  It installs a guard so no file input can open a native picker. `find` the dialog's
  file input, `file_upload` to it, click "Alternative text" and type, click Insert.
  The image lands with an empty paragraph on each side; that renders as nothing.
- **Coordinate clicks race the page.** A click aimed at one paragraph put the caret
  in another after the editor scrolled. `bc.caretBefore` places it with a `Range`.
- **When the toolbar is narrow, Insert image moves into "More options"**, but the
  `aria-label="Insert image"` button stays in the DOM and `bc.openInsertImage`
  finds it either way.
- **Prove persistence from the server, not the editor:** leave the editor (a
  "Leave site?" block means unsaved), open the preview from the drafts list, and
  run `bc.audit()` there. For tags, reopen the editor via the preview's Edit
  button; the preview page does not render them.
- **Closing a tab can dissolve the extension's tab group**, leaving the other tab
  outside it and uncontrollable. Close the tab you are still using last.

### The cover upload's file input is replaced as you use it

MEASURED 2026-09-21, create-article form. `find` returned the cover input as
`ref_963`; `file_upload` to it reported `Uploaded 1 file(s)` and **nothing
happened** — no thumbnail, no error text on the page, and the input's own
`files` read `0`. A `scroll_to` on the same ref then failed with *"No element
found with reference"*: React had replaced the node between the find and the
upload.

Re-running `find` gave `ref_1024`, and the identical upload to that ref
attached the file: a thumbnail with name, size and timestamp appeared within
four seconds, and the page began autosaving.

So **find the input immediately before uploading**, and judge the result by the
thumbnail rather than by the tool's success line or by `input.files`. Nothing in
either reports that the ref went stale.

A successful upload also gives the audit a landmark: the chip carries
`aria-label="file 1, <name>"`, which `bc.tagChips()` filters out and a cover
check can look for.

### Title and Description take a React value setter, not keystrokes

MEASURED 2026-09-21 on a hidden tab, where `computer type` drops keystrokes.
Both fields are `<textarea>` elements under React, so writing `.value` directly
is discarded on the next render. Going through the prototype's own setter and
dispatching `input` is what the component sees:

```js
const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
setter.call(field, text);
field.dispatchEvent(new Event("input", { bubbles: true }));
field.dispatchEvent(new Event("change", { bubbles: true }));
```

Title 62 characters and Description 206 both landed and autosaved this way, with
the tab never brought to the front. Read the lengths back off `.value`.

### Starting a new Builder Center article without the "+" menu

MEASURED 2026-09-21. With no drafts in the account, `/profile/content?tab=draft`
renders a **Create an article** button in the empty state, and it lands on the
same `/create/content/<id>?v=<v>` editor the top-bar "+" → Article does. One
click from a URL that can be navigated to directly, rather than two through a
menu that has to be found on screen.

### Auditing a Builder Center paste: there are no `<pre>` elements

MEASURED 2026-09-09. A clean paste of a 9-code-block article reports
`querySelectorAll('pre').length === 0`, which reads as total loss of every code
block. The blocks are all there. Builder Center renders them in its own widget:

```
div._code-snippet_  >  div._flex_  >  div._code-snippet-container_  >
  code.awsui_code-variant
```

So audit code by counting `code` elements whose text contains a newline, not by
counting `pre`. In that run: **9 multiline `code`** (the 9 fenced blocks) and
**133 single-line `code`** (the inline backticked identifiers), and the published
preview showed them with line numbers and syntax colouring.

Tables *do* arrive as real `<table>` — 4 tables, 39 `<tr>` in the same run — so
the table half of the audit works as written.

### `window.name` is safe for a Builder Center draft in progress

MEASURED 2026-09-09. The payload route needs a same-origin hop to localhost and
back, which means navigating away from a half-filled draft. That is safe here,
against the `/create/content/<id>?v=<v>` URL the editor is already on: the title
(118 chars) and description (353) were both intact on return, the draft id was
unchanged, and `window.name` still held all 18,405 characters.

The `/create/content/<id>` warning elsewhere in this kit is about editing an
**already-published** article. It does not apply to a draft you are still filling.
Verify anyway — read the field lengths back before pasting, since the cost of
being wrong is a duplicate article.

### Publishing runs a gate, and the first click is usually swallowed

Publish from the draft's own **preview** page (`/preview/content/<id>?v=<v>`, which the
drafts list links to) — it carries `Edit` and `Publish` next to each other. Two things
about that button, MEASURED 2026-08-30:

- **The first click does nothing.** Clicking the element by `ref` had no effect; a
  coordinate click on the same button opened the dialog. Judge by the dialog, not by
  the click result.
- **A "Checking" gate runs for ~10 s** — broken links, malicious links, profanity,
  title, description — plus SEO advice it will not block on ("title within 60
  characters", "description within 160"). Publication completes on its own when the
  checks pass, and the URL changes from `/preview/content/<id>?v=…` to
  `/content/<id>/<slug>`. That URL change is the confirmation; there is no banner.

**A hidden tab does not stop a publish, and a coordinate click does not start
one.** MEASURED 2026-09-21, `document.visibilityState === "hidden"` on the
preview page: two coordinate clicks on `Publish`, several seconds apart, did
nothing at all — no dialog, no gate traffic, no URL change. `window.focus()`
from the page did not make the tab visible either.

The same button then took the **`pointerdown → mousedown → pointerup → mouseup
→ click`** sequence — `bc.press(el)`, the route this file already records for
LinkedIn's buttons and for Builder Center's own code-block menu — on the first
try: the dialog opened, the gate ran, `reviewStatus` came back `PASSED`, and the
URL moved to `/content/<id>/<slug>`.

So the "first click does nothing" note above holds for a *visible* tab. On a
hidden one every coordinate click does nothing, and the difference between the
two cases is invisible from the click result, which is the same in both: a
success line and an unchanged page. **Read `document.visibilityState` before
concluding a button swallows clicks**, and reach for `press` rather than asking
the author to move a window.

A gate capture is not needed to publish. Hook `submit-review` and
`review-status` only when the gate has already refused — a passing gate
publishes on its own, so a capture run on a draft that might pass ships it.

**"Broken Links" / "Malicious Links" come from that gate, and its API names the
links.** MEASURED 2026-09-15: Publish sends `POST
https://api.builder.aws.com/cs/v2/content/submit-review` and then polls
`.../review-status`; both return
`contentIssues.{brokenLinks,maliciousLinks,profanityDetection}.violatedFragments`,
the exact URLs. The UI drops them and shows each generic message twice.
**`scripts/browser/builder-gate.js` packages this**: paste it on the preview page,
click Publish only while the draft is known to fail (a passing gate publishes
itself), then `await gate.wait(); gate.verdict()`. The bare hook it wraps, which
fills `window.__gate`:

```js
window.__gate = [];
const keep = (url, body) => { if (/submit-review|review-status/.test(url)) window.__gate.push({url, body}); };
const f = window.fetch;
window.fetch = async (...a) => { const r = await f(...a); r.clone().text().then(t => keep(String(a[0]?.url || a[0]), t)); return r; };
const o = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function (m, u, ...rest) {
  this.addEventListener("load", () => keep(String(u), this.responseText));
  return o.call(this, m, u, ...rest);
};
```

On the captured draft it named two `ai.google.dev` docs links, both as broken
*and* malicious, and passed dev.to, GitHub, a plain-text URL and everything else.
**It does not report every problem in one run.** The next capture, after those two
were replaced, flagged the plain-text `ai.google.dev/.../api-key` URL it had just
passed, plus a lone `/` left outside inline code by an earlier edit. Re-capture
after every fix until `reviewStatus` is no longer `FAILED`.
A guessed fix that removed three other suspects first did not clear it.
`preflight.py --live` now fails the same shape — an anchor that only resolves
through a sign-in or `oauth2callback` hop with no cookies — but the capture is
the ground truth.

**A draft whose title already appears under Published is a duplicate, not a revision.**
It is what the `/create/content/<id>` trap leaves behind, and it is a full copy of the
article with its own id, so nothing about it looks broken from the drafts list. Compare
ids before touching either: the published piece and its orphan differ only in id.

### Editing an already-published Builder Center article, measured

MEASURED 2026-09-20, adding a cover to a piece published minutes earlier. The
route in SKILL.md works and leaves no orphan: on the published page, the article's
own **vertical-dots menu -> Edit** lands on `/edit/content/<id>` -- note `/edit/`,
not the `/create/` URL that duplicates the article. The id in the URL is the
published article's, which is the thing to check before typing anything.

Two things about that editor:

- **It saves into a draft revision, not into the live article.** The cover upload
  autosaved with `Saved to your drafts` while the published page still showed no
  hero image. The edit only reaches readers after **Publish**, which republishes
  in place: same content id, same slug, no second article, and the gate runs again.
- **The Publish button swallows the first click here too**, and the page scrolls
  between the screenshot and the click often enough that a stale coordinate misses
  silently. Re-read the button's rect immediately before each attempt and judge by
  the URL returning to `/content/<id>/<slug>`, never by the click result.

The cover upload itself is as documented: `find` the file input, `file_upload` to
its ref. The widget then shows a preview card with the filename and size, which is
the confirmation -- the published page's `img` reporting `naturalWidth` 1200 is the
proof it went live.

### A scripted 200 proves nothing on builder.aws.com

MEASURED 2026-09-20, when the extension disconnected mid-publish and the obvious
move was to check the URL with `curl`. Both the article URL and its bare
`/content/<id>` form returned **200** -- and so did `/content/ZZZZnotarealcontentid0000`,
and so did a known-published article. Builder Center is a single-page app that
answers 200 for any path under `/content/`, so a fetched status cannot tell a
published article from one that never existed.

The control is the whole point: run the bogus id **before** believing the real
one. Publication state comes from the browser -- the URL moving from
`/preview/content/<id>?v=…` (or `/edit/content/<id>`) to `/content/<id>/<slug>` --
or from the drafts list. The same caution applies to the Medium copy for a
different reason: Cloudflare answers `curl` with **403 Attention Required**, which
is equally uninformative about whether the story is live.

## The screenshot is not in CSS pixels, and the gap is silent

MEASURED 2026-09-09 on Medium. `window.innerWidth` was **1673**; screenshots come
back **1568** wide. Every coordinate a `Range.getBoundingClientRect()` hands you is
in CSS pixels and lands ~6% right of where you meant. Three clicks in a row hit the
wrong text node — a double-click aimed at `IMPORTANT` selected `sbin` twelve
characters away — and each one *looked* like a normal miss rather than a systematic
offset, which is what made it expensive.

Two rules, and the second is the one that actually saves time:

- If you must use a JS-derived coordinate, scale it: `x * (screenshotWidth /
  window.innerWidth)`. Measure the factor, never assume 1.
- **Prefer reading the coordinate off the screenshot.** The click that finally
  worked came from looking at the rendered page and picking the boundary by eye.
  A `Range` rect is the right tool for deciding *what* to click and the wrong one
  for deciding *where*.

The same session's Builder Center clicks all landed first time, because those
coordinates were read from screenshots throughout.

**The gap is vertical too, and on Builder Center.** MEASURED 2026-09-21, tag
picker, `window.innerWidth` 1469: a click at a row's reported centre committed
**the row below it** — aimed at `cost-optimization` (rect centre y=656),
committed `cost-savings` (rect centre y=691). The rows are ~34px apart, so the
error was one row, consistently: `reported_y - 35` hit the intended row every
time afterwards, and clicking a reported centre hit its neighbour every time.

An offset of exactly one row is the expensive kind, because the result is a
plausible tag rather than a missed click, and the only signal is the chip's
name. Read the row off a screenshot, which is what the last two tags in that
session used, and read the chip back before moving on.

## Medium's Publish button also swallows the first click

MEASURED 2026-09-09. Documented above for Builder Center; it is true on Medium too.
The first click on `Publish` scrolled the page to the top and opened nothing. The
second, on the same element, opened the story-preview dialog. Judge by the dialog,
never by the click result — and re-screenshot before the second click, because the
first one moves the button.

## Opening Medium's publish dialog to set topics can publish the story

MEASURED 2026-09-21, on a draft that was meant to stay a draft. **It published.**

Medium keeps the topic field inside the story-preview dialog, and the only way
to that dialog is the Publish button. So "set the topics" and "publish" are the
same journey, and the dialog's default action is the irreversible one.

The sequence, all of it documented behaviour arriving in an order nobody had
written down:

1. Click `Publish`. The dialog opens. Focus stays on the button that opened it.
2. Click the topic field. **It does not take focus** — the same failure this
   file already records for that control, one step earlier than the commit
   routes it describes.
3. Type the topic. The field's `value` stays empty, so the keystrokes went to
   the page, where the focused element is still `Publish`.
4. The story goes out, with its `?postPublishedType=initial` URL, and the
   notification email with it.

The email cannot be recalled. The story can be reverted to a draft and keeps
its id and URL, so the link survives; the 230 subscribers who were emailed do
not un-receive it.

**So do not open that dialog on a draft.** Topics are worth less than an
unintended publish. Set them after publishing, when the dialog is the story
settings rather than a launch button, or leave them to Medium, which inferred
five reasonable ones by itself on the story above (`claude`, `mcp-server`,
`tools-and-resources`, `aws`, `cloud-billing`).

**If the dialog is already open, read the checkboxes with JS and believe them
over the screenshot.** Both read `checked: true` — Paywall and Notify — while
rendering unticked at 0.5 scale in the same second. The kit's existing advice
to read them back is right and the reason is stronger than "a stray keystroke
toggles them": the rendering is not evidence of the state at all.

**And the paywall checkbox did not decide the paywall.** It read `checked: true`
and the story published **not** paywalled — the RSS item carried the full
15,264-character body with no members-only marker. A checkbox that reads true
and does not take effect is worth knowing about before trusting either sense of
it: check the published story, not the dialog.

## Medium: a paste displaces a title typed before it

MEASURED 2026-09-21. Title typed into `.graf--title`, caret then placed in the
body by **clicking** the `Tell your story…` paragraph, then a `text/html` paste
of a 21,576-character document. Immediately after, the title block read
correctly. After a reload it was **empty**, and the 70 characters of title text
had been appended to the last list item of the references section, with no
separator: `…API_pricing_GetProducts.htmlPut the Arithmetic in the Tool: …`.

The payload carried no `<h1>` — the body began with a `<figure>` — so this is
Medium reflowing around the insert point rather than a heading in the paste.

The fix is this file's own re-paste routine, and the step that matters is the
`Return`: `ctrl+a`, `Delete`, type the title, **`Return`**, then paste. Placing
the caret in the body with a click instead of letting `Return` create the body
block is what produced the displacement. Same document, same payload, same
checksum, second attempt: title intact through a reload.

## Medium blocks a reload for minutes after it says "Saved"

MEASURED 2026-09-21. `beforeunload` stays registered for the life of the editor,
so `navigate` to the draft's own URL is refused with a "Leave site?" dialog even
when the header reads **Draft · Saved** and the content is on the server.

Read the save state from the header — zoom the top strip, it is the word beside
`Draft` — and then navigate with `force: true`. Both times that was done here
the reloaded document was complete. `window.name` survives the forced reload, so
the payload does not have to be carried in again.

## Medium's topic picker: clicking a suggestion does nothing

MEASURED 2026-09-09. Typing `Linux` in the story-preview dialog's topic field
raises a suggestion list (`Linux (16.7K)`, `Linux Tutorial (2.3K)`, …). **Clicking
a row does not add a chip** — tried twice, at the text and at the row centre, and
the field stayed on its `Add a topic...` placeholder both times. What works is
**type, wait, `ArrowDown`, `Return`**. The placeholder then flips to
`Add more topics...`, which is the acceptance signal to check.

Clicking a suggestion also *drops focus* — `document.activeElement.placeholder`
reads `NONE` afterwards — which is how a stray keystroke reaches the page and the
paywall/notify checkboxes. The keyboard route keeps focus in the field for the
next topic.

**MEASURED 2026-09-20: the keyboard route failed here and a synthetic mouse
sequence worked — the reverse of the run above.** Publishing paper 4 of
`lakehouse-iceberg-2026`, `type -> ArrowDown -> Return` left the suggestion list
open and scrolled the dialog instead of committing; no chip appeared. What
worked, three topics out of three, was dispatching `pointerdown, mousedown,
pointerup, mouseup, click` as `MouseEvent`s on the option row (`el.closest('li')
|| el`) — the same route line 623 records for Builder Center's tag picker, which
that section calls Medium's exact opposite. A bare `Return` with no `ArrowDown`
did commit the **first** topic, with focus still in the field from the click that
opened it, and then failed for the next three. One trial of each route, so this
is a contradiction to explain rather than a new rule to follow.

Two consequences. Neither route can be assumed, so read the chips back after
every topic rather than trusting either — `Add a topic...` -> `Add more topics...`
is still the acceptance signal. And a failed commit leaves focus in the field
while swallowing the term: three `type` calls in one batch concatenated into
`mcppythondata engineering` in the input rather than landing on the page, so the
checkbox hazard above did not fire that time. It is the same hazard either way;
re-read the checkbox states before Publish, which is what caught the difference
here.

## An assertion inside a batch cannot gate the batch

MEASURED 2026-09-09, and it is the mechanism behind the checkbox hazard above.
Batching `click → assert focus → type` runs the type **whatever the assertion
returned**; the assertion is a log line, not a guard. The run that produced this
note asserted `placeholder: NONE` and typed `Debian` into the page anyway. The
checkboxes survived by luck.

Put the assertion in its own call and read it before sending the keystrokes.

## A domain the tab has not visited fails inside a batch, not standalone

MEASURED 2026-09-09. `navigate` to `medium.com` inside a `browser_batch` returned
`Navigation to this domain is not allowed` and stopped the batch. The identical
navigate, called standalone, succeeded immediately. The per-item permission check
runs ahead of the batch and cannot prompt.

This reads exactly like a missing site permission and is not one. **Retry
standalone before telling the user to grant anything.**

## Free the browser when you are done

The user works in these same tabs. Close what you opened as soon as the draft is
saved; do not sit on a Builder Center tab while they wait for it.

## Getting a payload into an editor: use `window.name`

MEASURED 2026-08-31, and it replaces the chunked injection for any editor whose
page you can navigate to.

`window.name` **survives a cross-origin navigation in the same tab.** So the
payload can be loaded same-origin from localhost, stashed, and read back on the
destination:

```js
// on http://127.0.0.1:8901/<file>  -- same origin, so fetch is allowed
window.name = await (await fetch(location.href)).text();
// then navigate the SAME tab to the editor, and there:
const html = window.name;      // intact
```

34,715 characters carried into `medium.com/new-story` with an identical Adler
checksum on both sides. No chunk loop, no cumulative length check, no system
clipboard, and no CSP problem — the fetch happens on the origin that allows it.

Cross-origin `fetch` into the editor stays blocked. Confirmed on Medium as well as
Builder Center: `fetch('http://127.0.0.1:...')` from `medium.com/new-story` fails
with a bare `TypeError: Failed to fetch`.

## The checksum in SKILL.md is UTF-16, and that is a trap

`charCodeAt` iterates **UTF-16 code units**. Python's `for ch in text` iterates
**code points**. Any astral character — every emoji, so every article in this
house style — counts as 2 in JavaScript and 1 in Python, and the two checksums
disagree on a payload that transferred perfectly.

MEASURED: a 34,712 code-point document containing three `🔎` reported 34,715
characters in the browser. Adler mismatched on the same bytes. Computing the local
side over UTF-16 code units reproduced the browser exactly:

```python
units = text.encode("utf-16-le")
a = b = 0
for i in range(0, len(units), 2):
    a = (a + int.from_bytes(units[i:i+2], "little")) % 65521
    b = (b + a) % 65521
```

Comparing raw character counts across the two languages has the same flaw. **A
checksum that cries corruption on correct data gets switched off**, which is worse
than not having one.

## Pasting into Medium, measured end to end

Dispatching a `paste` with `text/html` from `window.name`, into an editor asserted
empty first:

| Checked | Result |
| --- | --- |
| images | 7, every `src` under `0*` — Medium re-hosted all of them |
| code blocks | 39, preserved as real multi-line blocks |
| headings | 19 `h4` + 1 `h3`, no `h1`/`h2` — the demotion held |
| landmarks | opening, cheat sheet and closing each exactly once |
| `dispatchEvent` | returned `false` — `preventDefault`, and the paste worked |

**The title still does not transfer.** The `graf--title` block is left empty and
the pasted `<h1>` lands as an ordinary body heading, so the title appears twice
once you type it in. Type the title, then delete the duplicate heading.

**Deleting that heading with two Backspaces merges it into the next paragraph**,
which inherits the heading style — the opening paragraph silently became a
heading. Select that paragraph and toggle the large-`T` button off to restore it.
Reproduced on a second run, so it is the behaviour and not an accident: expect it,
and check the opening paragraph's tag afterwards rather than trusting the delete.

## Re-pasting over an existing draft

`Ctrl+A` then `Delete` clears the body — **but only if the caret is in a text
block.** MEASURED: clicking at a coordinate that landed on the cover figure put
the caret in the Title field instead, `Ctrl+A` selected the title, and the body
survived untouched at 19,528 characters. The emptiness assertion caught it and
refused to paste; without that assertion the article would have been appended to
itself. Click a **paragraph**, not an image, and never judge the clear by the
keystrokes having been sent.

`Ctrl+A` also clears the Title field, so the title has to be retyped after a
re-paste, and the duplicate-heading dance repeats.

## Do not repair a Medium draft with execCommand deletes

MEASURED 2026-08-31, and it cost the draft.

`document.execCommand("delete")` over a full selection **works** on Medium, unlike
on Builder Center where it silently no-ops. It cleared 28,690 characters to 1. But
using it — along with programmatic `Range` deletions of individual blocks — left
the editor in a state Medium could not persist:

> Something is wrong and we cannot save your story.

The banner cleared briefly after a real keystroke and came straight back. The tab
then refused to navigate away, because nothing had been saved. Discarding was the
only exit, and the draft came back half-written at 24,252 characters.

**Repair a draft by replacing it, not by editing it.** Click a body paragraph,
confirm the caret is there, real `Ctrl+A` then `Delete`, assert empty, dispatch
the paste. That saved cleanly on the retry and every check passed.

## Verify the caret, because the click races the page

The coordinate is measured, then the page scrolls, then the click lands elsewhere.
Twice in a row a click aimed at a body paragraph put the caret in the **Title**,
where `Ctrl+A` selects the title and `Delete` takes it while the body survives.

```js
const n = getSelection().anchorNode;
const el = n && (n.nodeType === 3 ? n.parentElement : n);
el.closest('.graf--title')        // must be null before Ctrl+A
```

A `Range` avoids the race but does not give the keystrokes the focus they need —
a synthetic caret did not make `Ctrl+A` clear the body. Click, verify, re-click.

## Builder Center: a WAF silently drops saves whose body matches an attack signature

MEASURED 2026-09-04, and it cost most of a session because every symptom points
somewhere else. The editor shows **"Failed to save your drafts"**, the body is
absent after reload, and the request never appears with a status — instrumenting
`window.fetch` shows the save `PATCH` throwing **`TypeError: Failed to fetch`**
and being retried three times. That is a network-level drop, not a 503 and not
an application error, so there is no response body to read.

The give-away is that the app sends **two** PATCHes to the same URL. The small
metadata one (`versionId`, `heroImageUrl`, `tags`) returns 200; the one carrying
`markdownDescription.articleMarkdownDescription` is the one dropped. A draft
whose title and cover save while the body vanishes is this, every time.

**Do not conclude a size limit.** Bodies grew to 1,498 characters with every
PATCH returning 200, while a single 1,253-character paste was dropped — because
the *content* differed, not the length. Confirm by replaying the save yourself
from the page, which needs no auth to be conclusive: a request that reaches the
server returns **401** (missing the app's own header), one the WAF drops still
throws `Failed to fetch`.

```js
const probe = async (text) => {
  const body = JSON.stringify({ versionId: VID,
    markdownDescription: { articleMarkdownDescription: text } });
  try { const r = await fetch(URL, { method:"PATCH", credentials:"include",
          headers:{ "Content-Type":"application/json" }, body });
        return r.status; }          // 401 = passed the WAF
  catch (e) { return "BLOCKED"; }   // never left the browser
};
```

Bisect the body with that probe — window it, then shrink from both ends — and it
names the offending span in about fifteen requests. Two spans did it here, both
ordinary technical prose:

| what tripped it | why | fix that keeps the meaning |
|---|---|---|
| `grep -cE '^    (get\|post\|delete\|head\|put):' irc.yaml` | single-quoted string starting with `^` containing an alternation — a regex-injection signature | use **double quotes**: `"^    (get\|post…):"`. Identical in bash, and identical in Python for `r'...'` → `r"..."` |
| ``as `open-api/rest-catalog-open-api.yaml` and`` | bare relative path ending `.yaml` — a path-traversal/LFI signature | split it: ``as `rest-catalog-open-api.yaml`, under `open-api/`,`` |

Both rules are scored rather than absolute: the same path passed in isolation and
was dropped inside its sentence, so **re-probe the whole body after each edit**
rather than trusting a minimal repro. Windowing all 14 KB in 500-character
slices takes 29 requests and finds every remaining span.

Nothing else was the cause. The synthetic `ClipboardEvent` from the JS bridge
**does** update the editor's model and **does** trigger a save — a 290-character
paste saved through exactly that path. Chunking, real typing and the clipboard
were all dead ends chased before the WAF was found.

**Verify persistence through the drafts list, never a `?v=` URL.** Those pin a
version and serve stale content, so a reload of one shows an empty body long
after the save succeeded. Load `/profile/content?tab=draft`, take the
`/preview/content/<id>?v=<v>` link it gives, and read that.

## Builder Center's tag picker is the mirror image of Medium's

MEASURED 2026-09-15. Medium's topic field ignores a click and takes
`type → ArrowDown → Return`. Builder Center's tag field is the exact opposite, and
reaching for Medium's route first costs several wasted attempts.

The control is an `input[role=combobox]` over a virtualised `[role=listbox]`.
Selection is `aria-selected` on the row, and `bc.tagChips()` reads the committed
chips.

**Correction, MEASURED 2026-09-21: the rows do render a checkbox.** Each option
in the create-article form drew one, unchecked, and the checked row's box filled
blue — visible in a screenshot and matching the chip that appeared. This file
previously said rows carry no checkbox element, from a 2026-09-15 run on the
same control. Whether the difference is the form (create rather than edit) or a
change to the component is not established, so read `aria-selected` either way:
it was correct in both runs, and a checkbox audit is correct in neither.

| route | result |
|---|---|
| `element.click()` on the row | nothing; `aria-selected` stays `false` |
| `Return` with the list filtered to one row | nothing; `aria-activedescendant` is `null`, so no row is formally active |
| real mouse click on the filtered row | **commits** — the row reads `Selected` and a chip appears under the field |
| **`press(row)`: `pointerdown → mousedown → pointerup → mouseup → click`** | **commits** (MEASURED 2026-09-21) |

**`press` commits it, and that changes the whole loop.** MEASURED 2026-09-21:
five tags committed first time, from a `hidden` tab, with no coordinate click
anywhere — which removes both of the things that made this control expensive.
The one-row click offset below cannot happen, because nothing is aimed at a
pixel; and the tab does not have to be brought to the front, so there is no
step that needs the author.

`element.click()` alone still selects nothing, so the row wants the pointer and
mouse events before it. That is the same sequence Medium's topic picker needed
in its 2026-09-20 run and the same one Builder Center's own Publish button
needs on a hidden tab — three controls, one route, and worth trying first on
the fourth.

The whole tag loop then scripts, with two conditions it has to keep: re-open the
field only when no `input[role=combobox]` is present (pressing the field while
the control is already open closes it), and write the filter through the input's
React value setter rather than typing it:

```js
const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
setter.call(box, slug);
box.dispatchEvent(new Event("input", { bubbles: true }));
```

Then filter the rendered rows for an exact slug match, `press` that row, and read
the chips back before the next one.

**A click a few pixels off the row tears down the whole control.** Not just the
list: `input[role=combobox]` and `[role=listbox]` both leave the DOM, so the next
`box.focus()` throws `Cannot read properties of null`. That exception means the
dropdown was dismissed, not that the page broke. Re-open by clicking the closed
field. Committed chips only exist in the DOM while it is open, so read them from
the field itself, or from a screenshot.

Because the list is virtualised, only the rendered window exists. Probing the whole
taxonomy for selected rows is meaningless — search the exact slug and read that
row's `aria-selected`.

That route is in `scripts/browser/builder-editor.js`: `bc.tagSearch(slug)` filters
the list and returns the **point to click with a real mouse** (it does not click,
because a synthetic one selects nothing), `bc.tagStatus(slug)` reads that row's
`aria-selected`, and `bc.tagChips()` reads the committed chips. Both refuse, rather
than throwing, when the control has been torn down by an off-row click.

**A search that returns nothing is usually a collapsed field, not a missing
tag.** MEASURED 2026-09-21: `mcp`, `generative` and `agent` each returned zero
rows and read as absent from the vocabulary. All three were typed into a control
that had torn itself down when the previous tag committed — `document.activeElement`
was `BODY`, and there was no `input[role=combobox]` in the DOM at all. Re-opening
the field and typing `mcp` returned five rows: `mcp`, `mcp-server`,
`mcp-integration`, `aws-mcp-server`, `aws-knowledge-mcp`.

**The field collapses after every commit**, so a tag loop has to re-open it each
time, and the field *moves* as it goes: chips render **below** the input, so each
committed tag pushes nothing down but grows a row under it that a stale
coordinate then lands in — a click meant for the field hit a chip's Remove
button instead. Read the field's position again before every re-open, and read
the chips back after every commit rather than after the loop.

**Not every subject has a tag, and a miss looks like a broken control.** `iceberg`
returns nothing at all. `lakehouse` returns only `amazon-sagemaker-lakehouse`.
Search the AWS product vocabulary instead: `agents` → `strands-agents`,
`ai-agents`, `amazon-bedrock-agents`; `analytics` → `data-analytics`; `storage` →
`object-storage`; `generative` → `generative-ai`.

## `new Response(stream)` is blocked on Builder Center, with nothing on the wire

MEASURED 2026-09-15. The usual way to gunzip a payload inside the page —

```js
const text = await new Response(blob.stream().pipeThrough(new DecompressionStream("gzip"))).text();
```

— works on `medium.com` and throws **`TypeError: Failed to fetch`** on
`builder.aws.com`, while reading a `Blob` that is already in memory. The error is
word-for-word the cross-origin fetch failure documented above, so it reads as a
network problem when no request is being made.

Read the stream directly; this works on both:

```js
const ds = new DecompressionStream("gzip");
const w = ds.writable.getWriter(); w.write(bytes); w.close();
const r = ds.readable.getReader();
const parts = []; let n = 0;
for (;;) { const {done, value} = await r.read(); if (done) break; parts.push(value); n += value.length; }
const merged = new Uint8Array(n); let o = 0;
for (const p of parts) { merged.set(p, o); o += p.length; }
const text = new TextDecoder().decode(merged);
```

## Medium's real title block also reports a negative `top`

MEASURED 2026-09-15. This kit already warns that `[contenteditable="true"]` returns
a hidden 100x100 decoy parked at `x=-9999`. After a long paste there is a second
way to be fooled: the page is left scrolled ~10,000px down, so **every** element
above the viewport reports a large negative `top` — the real title block included.

`H3.graf--h3.graf--empty.graf--leading.graf--title` read `rect=497,-9990`, which is
indistinguishable from the decoy by rect alone. `window.scrollTo(0, 0)` first; it
then reads `497,88`, is clickable, and accepts the typed title.

Distinguish the two by class, never by position: the decoy carries no `graf`
classes and is 100x100; the title is `.graf--title` at the editor's full column
width.

A single `.graf--empty` at the **end** of the document is Medium's normal trailing
paragraph, not the stray block a dropped `<h1>` leaves at the top. Check where it
sits before running the Backspace routine at it.

## A cell's height is not its line count

MEASURED 2026-09-15, chasing a table column that wrapped on dev.to. Dividing an
element's `clientHeight` by its `line-height` measures the **row's tallest cell**,
not the text's lines, so a one-line cell in a two-line row reports two lines. Three
"fixes" shipped against that false reading before the measurement was corrected.

`Range.getClientRects().length` returns one rect per rendered line box, and is the
honest count:

```js
const n = [...cell.childNodes].find(x => x.nodeType === 3 && x.textContent.trim());
const rg = document.createRange(); rg.selectNodeContents(n);
const lines = rg.getClientRects().length;
```

Cross-check against the width the text needs unbroken, from a `white-space: nowrap`
clone in the same font. The two agreeing is what makes a negative result mean
anything.

**The wrap itself:** an auto-layout table column is sized to its *minimum content
width* — the longest unbreakable word. `Test 1` therefore breaks to `Test` / `1` at
**every** viewport width, and shortening the label shrinks the column with it, so
the wrap survives every time. Remove the break opportunity instead: a single token
(`1`), not shorter text.
