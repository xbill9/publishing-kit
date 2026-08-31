# Driving the editors in a browser

> **First: is there an API?** dev.to has one, and this repo already wraps it in
> `publish-devto.sh` (present in eight rigs, generic, takes any article path). A
> whole browser flow was once built for dev.to while that script sat unused. Check
> the repo for a publish script before opening a tab. The browser is the fallback
> for destinations with no API — currently Medium and AWS Builder Center.


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

```js
const md = new TextDecoder().decode(Uint8Array.from(atob(b64), c => c.charCodeAt(0)));
const eds = [...document.querySelectorAll('[contenteditable="true"]')];
const ed = eds[eds.length - 1];
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
- **Changing one word:** get the character's rect from a `Range`, click at its
  right edge, confirm the caret with `getSelection().anchorOffset` and the
  surrounding text, then type. Do not double-click a one- or two-letter word — at
  that size the hit lands on the neighbouring space and selects that instead.

### Pasting inserts empty blockquotes

A paste that contains a blockquote arrives with **empty blockquotes wrapped around
the real one** — 3 empties around 1 real, in the measured case. Unlike the
importer's empty code blocks (which do not render publicly), these show as blank
quoted gaps. Count blockquotes against the source and delete the empties with the
click-and-Backspace route above.

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
   count and that each `src` is re-hosted (`miro.medium.com` / `0*`), heading level,
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

The published URL is `<user>.medium.com/<slug>-<id>`, a different origin from
`medium.com` — so the extension's per-domain permissions may not cover it, and
`screenshot` / `javascript_tool` start failing there while `get_page_text` still
works. Medium also answers `curl` with **403**, so verify the published article
with `get_page_text` in the browser, not from the shell.

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

**A draft whose title already appears under Published is a duplicate, not a revision.**
It is what the `/create/content/<id>` trap leaves behind, and it is a full copy of the
article with its own id, so nothing about it looks broken from the drafts list. Compare
ids before touching either: the published piece and its orphan differ only in id.

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
