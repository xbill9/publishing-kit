// AWS Builder Center editor helpers, for evaluation in the browser page.
//
// MEASURED 2026-09-15 while repairing a live draft. Each helper exists because the
// obvious route failed silently:
//
//   - The editor tab is often `document.visibilityState === "hidden"` under the
//     extension. Keystrokes sent with `computer type` were DROPPED there -- no text
//     landed anywhere -- and screenshots timed out. A synthetic ClipboardEvent
//     paste over a Selection still updates the editor's model and autosaves, so
//     every text edit below goes through `pasteOver`, never through typing.
//   - Coordinate clicks race the page's own scrolling: a click aimed at one
//     paragraph put the caret in another. Place the caret with a Range instead.
//   - Code blocks are non-editable widgets. Their text is edited in an
//     "Edit code block" dialog that hosts an Ace editor; `setValue` on it works.
//   - "Insert image" rejects external URLs ("Invalid image URL") and the body
//     silently drops markdown images on save. Images must be uploaded through the
//     dialog's own <input type=file> (find it, then `file_upload` with its ref).
//
// Paste this whole file once per page load (it only defines functions on
// window.bc), then call e.g. `await bc.replaceText("old", "new")`.
// Every mutating helper verifies its precondition and RETURNS {refused: ...}
// instead of acting when it does not hold -- a guard inside one script is a real
// guard, unlike an assertion inside a browser_batch.

window.bc = (() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const visible = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };

  // The body editor is the wide contenteditable; table cells are narrow ones.
  const editor = () =>
    [...document.querySelectorAll('[contenteditable="true"]')].find((e) => e.getBoundingClientRect().width > 200);

  const dialog = () => [...document.querySelectorAll('[role=dialog],[aria-modal=true]')].find(visible) || null;

  const textNodes = (root) => {
    const out = []; const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n;
    while ((n = tw.nextNode())) out.push(n);
    return out;
  };

  const select = (startNode, startOff, endNode, endOff) => {
    const ed = editor(); ed.focus();
    const r = document.createRange(); r.setStart(startNode, startOff); r.setEnd(endNode, endOff);
    const s = getSelection(); s.removeAllRanges(); s.addRange(r);
  };

  // Replace the current selection with text/plain. Markdown in `text` is converted
  // by the editor's paste handler, so "[label](https://...)" becomes a real link.
  const pasteOver = async (text) => {
    const ed = editor(); const dt = new DataTransfer(); dt.setData("text/plain", text);
    ed.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
    await sleep(1200);
  };

  // Click a button the way React listens for it; plain .click() alone did not open
  // the code-block options menu.
  const press = (el) => {
    for (const t of ["pointerdown", "mousedown", "pointerup", "mouseup"])
      el.dispatchEvent(new (t.startsWith("pointer") ? PointerEvent : MouseEvent)(t, { bubbles: true, cancelable: true, button: 0 }));
    el.click();
  };

  // Replace one exact substring that lies inside a single text node.
  async function replaceText(oldStr, newStr) {
    const ed = editor(); if (!ed) return { refused: "no body editor" };
    const hits = textNodes(ed).filter((n) => n.textContent.includes(oldStr));
    if (hits.length !== 1) return { refused: `expected 1 text node containing it, found ${hits.length}` };
    const n = hits[0]; const i = n.textContent.indexOf(oldStr);
    n.parentElement.scrollIntoView({ block: "center" });
    select(n, i, n, i + oldStr.length); await sleep(400);
    if (getSelection().toString() !== oldStr) return { refused: "selection mismatch", sel: getSelection().toString() };
    await pasteOver(newStr);
    return { replaced: true, remaining: editor().innerText.split(oldStr).length - 1 };
  }

  // Replace the whole text of a block (li, p, h4) whose innerText equals `exact`.
  // Use this for link text: the selection starts outside the anchor, so the pasted
  // text does not inherit the old href.
  async function replaceBlock(exact, newText, tags = "li,p,h4") {
    const ed = editor(); if (!ed) return { refused: "no body editor" };
    const blocks = [...ed.querySelectorAll(tags)].filter((b) => b.innerText.trim() === exact);
    if (blocks.length !== 1) return { refused: `expected 1 block, found ${blocks.length}` };
    const t = textNodes(blocks[0]); blocks[0].scrollIntoView({ block: "center" });
    select(t[0], 0, t[t.length - 1], t[t.length - 1].length); await sleep(400);
    if (getSelection().toString() !== exact) return { refused: "selection mismatch", sel: getSelection().toString() };
    await pasteOver(newText);
    return { replaced: true, links: [...ed.querySelectorAll("a")].map((a) => a.href) };
  }

  // Put the caret at the start of the paragraph beginning with `prefix`. Then send
  // real keys `Return Up` to open an empty slot above it, and check with
  // caretSlot(prefix) before inserting anything there.
  async function caretBefore(prefix) {
    const ed = editor(); if (!ed) return { refused: "no body editor" };
    const p = [...ed.querySelectorAll("p")].filter((x) => x.innerText.startsWith(prefix));
    if (p.length !== 1) return { refused: `expected 1 paragraph, found ${p.length}` };
    p[0].scrollIntoView({ block: "center" });
    const first = textNodes(p[0])[0]; select(first, 0, first, 0); await sleep(600);
    return { caretAt: prefix, offset: getSelection().anchorOffset, focused: document.activeElement === ed };
  }

  // True when the caret sits in an empty paragraph directly above `nextPrefix`.
  function caretSlot(nextPrefix) {
    const n = getSelection().anchorNode; const el = n && (n.nodeType === 3 ? n.parentElement : n);
    const p = el && el.closest("p");
    return {
      inEmptyParagraph: !!p && p.innerText.trim() === "",
      nextStartsWith: !!p && (p.nextElementSibling?.innerText || "").startsWith(nextPrefix),
      focused: document.activeElement === editor(),
    };
  }

  // Open the Insert image dialog at a verified slot. Installs a guard first so a
  // file input's .click() cannot open a native picker (which the extension can
  // neither see nor dismiss). Then: find the dialog's file input -> file_upload,
  // click "Alternative text" -> type, click "Insert".
  async function openInsertImage(nextPrefix) {
    const slot = caretSlot(nextPrefix);
    if (!slot.inEmptyParagraph || !slot.nextStartsWith || !slot.focused) return { refused: "caret not in a verified slot", ...slot };
    if (!window.__bcPickerGuard) {
      window.__bcPickerGuard = HTMLInputElement.prototype.click;
      HTMLInputElement.prototype.click = function () { if (this.type === "file") { window.__bcPickerBlocked = true; return; } return window.__bcPickerGuard.call(this); };
    }
    const btn = [...document.querySelectorAll("button")].find((b) => b.getAttribute("aria-label") === "Insert image");
    if (!btn) return { refused: "no Insert image button (toolbar may be collapsed into More options)" };
    press(btn); await sleep(1500);
    const d = dialog();
    return { opened: !!d, fileInputs: d ? d.querySelectorAll("input[type=file]").length : 0, pickerBlocked: !!window.__bcPickerBlocked };
  }

  // Replace a substring inside a code block. The block is a widget: open its
  // options menu, choose Edit, set the Ace editor's value, Save.
  async function replaceInCodeBlock(oldStr, newStr) {
    const ed = editor(); if (!ed) return { refused: "no body editor" };
    const codes = [...ed.querySelectorAll("code")].filter((c) => c.innerText.includes(oldStr.trim().slice(0, 60)));
    if (codes.length !== 1) return { refused: `expected 1 code block, found ${codes.length}` };
    let w = codes[0]; while (w.parentElement && w.parentElement !== ed) w = w.parentElement;
    const opts = w.querySelector('button[aria-label="Code block options"]');
    if (!opts) return { refused: "no Code block options button" };
    opts.scrollIntoView({ block: "center" }); press(opts); await sleep(1200);
    const edit = [...document.querySelectorAll('[role=menuitem],[role=menu] li,[role=menu] button')].filter(visible).find((m) => m.innerText.trim() === "Edit");
    if (!edit) return { refused: "options menu did not open" };
    press(edit); await sleep(1500);
    const d = dialog(); const aceEl = d && d.querySelector(".ace_editor");
    const ace = aceEl && (aceEl.env?.editor || (window.ace && window.ace.edit(aceEl)));
    if (!ace) return { refused: "no Ace editor in the dialog" };
    const before = ace.getValue(); const count = before.split(oldStr).length - 1;
    if (count !== 1) return { refused: `expected 1 occurrence in the block, found ${count}` };
    ace.setValue(before.replace(oldStr, newStr), 1); await sleep(400);
    const save = [...d.querySelectorAll("button")].find((b) => b.innerText.trim() === "Save");
    press(save); await sleep(2000);
    return { replaced: true, dialogClosed: !dialog(), stillPresent: editor().innerText.includes(oldStr) };
  }

  // Counts to compare against the source after any edit. On a preview page (no
  // editor) it reads the document instead, which is what proves persistence.
  function audit(landmarks = []) {
    const root = editor() || document.querySelector("main") || document.body;
    const t = root.innerText;
    return {
      chars: t.length,
      images: [...root.querySelectorAll("img")].filter((i) => /cosmic\.aws\.dev/.test(i.src)).map((i) => ({ file: i.src.split("/").pop().split("?")[0].slice(-40), alt: (i.alt || "").length, loaded: i.complete && i.naturalWidth > 0 })),
      codeBlocks: [...root.querySelectorAll("code")].filter((c) => c.innerText.includes("\n")).length,
      tables: root.querySelectorAll("table").length,
      links: [...new Set([...root.querySelectorAll("a")].map((a) => a.href).filter((h) => /^https?:/.test(h) && !/builder\.aws\.com|aws\.amazon\.com|pulse\.aws/.test(h)))],
      tags: [...document.querySelectorAll('[aria-label^="Remove "]')].map((e) => e.getAttribute("aria-label").slice(7)).filter((x) => x !== "hero image"),
      landmarks: Object.fromEntries(landmarks.map((l) => [l.slice(0, 30), t.split(l).length - 1])),
      saveErrors: [...document.querySelectorAll("span,div,p")].filter((e) => visible(e) && e.childElementCount === 0).map((e) => e.textContent.trim()).filter((x) => /failed to save|invalid image/i.test(x)),
    };
  }

  return { editor, dialog, pasteOver, press, replaceText, replaceBlock, caretBefore, caretSlot, openInsertImage, replaceInCodeBlock, audit };
})();
Object.keys(window.bc);
