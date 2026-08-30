# Driving the editors in a browser

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

## Medium

- Paste `-hosted.html`, never `-embed.html`. See `medium.md` — the embed variant
  loses every image.
- Type the title by hand; no paste route fills it.
- The editor autosaves and shows `Saved`; the URL changes to `/p/<id>/edit` on the
  first save. That id is the draft link.
- **Importing cannot update an existing draft.** It always creates a new one, so a
  revised article means a new draft and deleting the old one by hand.

## AWS Builder Center

- New article: **"+" in the top bar → Article.** Never open an existing draft's
  preview to edit — that overwrites the other piece. This matters more than it
  sounds: the user often has another draft in flight in a parallel tab.
- The page loads as skeleton placeholders first. Wait for it, or clicks land on
  nothing.
- Title and Description are ordinary inputs; click and type. Body is the
  `contenteditable` — use the JS bridge above.
- Tables and multi-line code both render natively. No image conversion.
- **The cover must be uploaded by hand** (drag-and-drop in the editor). There is no
  headless route, so hand this step back explicitly rather than leaving the draft
  looking finished.
- It autosaves — "Saved to your drafts", no save button.

## Free the browser when you are done

The user works in these same tabs. Close what you opened as soon as the draft is
saved; do not sit on a Builder Center tab while they wait for it.
