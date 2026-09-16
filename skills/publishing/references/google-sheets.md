# Google Sheets, measured

A sprint or program often tracks published work in a shared Google Sheet, so the
last step of a publishing run can be "add a row". **Every technique that works on
the editors in this kit fails here**, and each item below cost at least one wasted
attempt.

MEASURED 2026-09-16 against an external shared tracking sheet.

## The grid is a canvas. There is nothing to read in the DOM

`document.querySelectorAll('canvas').length === 1`, and that one canvas is the
whole grid. There are **no** `[role=grid]`, `[role=row]` or `[role=gridcell]`
nodes, and the cell-ish classes that do exist (`range-border`, `cell-input`) carry
no text. A DOM scrape returns nothing and reads exactly like a page that has not
finished loading.

Two things outside the canvas *are* ordinary DOM, and they are the way in:

| element | selector | use |
|---|---|---|
| Name Box | `#t-name-box` | navigate to any cell or range |
| formula bar | `#t-formula-bar-input` | read the selected cell's exact contents |

## Reading: drive the Name Box, read the formula bar

Set the value, dispatch a full Enter triple, wait, read:

```js
const nb = document.querySelector('#t-name-box');
const fb = () => document.querySelector('#t-formula-bar-input')
                         .innerText.replace(/ /g, ' ').trim();
async function read(ref) {
  nb.focus(); nb.select(); nb.value = ref;
  nb.dispatchEvent(new Event('input', { bubbles: true }));
  for (const t of ['keydown', 'keypress', 'keyup'])
    nb.dispatchEvent(new KeyboardEvent(t, { key: 'Enter', code: 'Enter',
                                            keyCode: 13, which: 13, bubbles: true }));
  await new Promise(r => setTimeout(r, 400));
  return fb();
}
```

This returns the cell's true text, including everything a screenshot truncates —
which is the only way a 1,035-character description cell can be read at all.

**An empty cell reads as `''` trimmed, or `'\n'` untrimmed.** Do not mistake a
`length === 1` newline for content.

**Keep a batch to about ten same-sheet cells.** At ~400ms each that sits well
inside the tool's 45-second budget. **Cross-sheet references
(`'Suggested Projects'!A9`) are much slower** — ten in a loop timed out the CDP
call twice running, on a tab that answered a one-line `document.title` instantly.
When a renderer looks frozen, prove it with a trivial call before concluding
anything.

A screenshot is fine for getting the shape of many columns at once. For any value
you intend to rely on, read the cell.

## Writing: `computer type` sends literal tabs, not Tab keys

MEASURED, at the cost of a full undo. Typing a tab-separated row put **all 2,141
characters into the first cell** as a single string containing literal `\t`, and
the trailing newline dropped a stray `\n` into the row below. The `type` action
types characters; it does not press Tab.

**What works is a synthetic paste of TSV** — exactly how Sheets fills a range, and
it never touches the system clipboard, which this kit forbids anyway:

```js
// select the first cell of the target row first, via the Name Box
const tsv = cells.join('\t');            // one entry per column, '' for blanks
const dt = new DataTransfer();
dt.setData('text/plain', tsv);
document.activeElement.dispatchEvent(
  new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
```

`dispatchEvent` returns **`false`**. That is `preventDefault` — Sheets handled it —
the same signal the Medium and Builder Center bridges give. With a cell selected
the target is `DIV.cell-input`. Judge by reading the cells back, never by the
return value.

Eighteen values, including a 1,035-character cell and a 336-character cell,
distributed across columns A–R in one event.

## Undo is per-session and safe

`ctrl+z`, repeated, reverted the bad write completely: the target cell and the two
cells the stray newline touched went empty. Rows written by other people were
untouched — **verify that by reading a couple of their rows back**, because on a
shared sheet the cost of being wrong is somebody else's data.

## Scrolling the grid

`computer scroll` with `scroll_direction: right` does nothing on the canvas. Moving
the *selection* moves the view: click a cell in the row, then `ctrl+Right` jumps to
the last column of the contiguous block — which is also how to learn how many
columns a sheet actually uses.

## Always read the row back

The write returns nothing meaningful and a screenshot shows truncated cells. Read
every written cell through the formula bar and compare it with what you meant to
write. It is the only check that tells "wrote the row" apart from "wrote the whole
row into one cell".
