// LinkedIn composer helpers, for evaluation in the page on linkedin.com/feed.
//
// MEASURED 2026-09-15 posting an article announcement with its cover image. Why each
// helper exists is in references/linkedin.md ("Attaching the cover and posting").
// Short version: the tab is often hidden (ref clicks do nothing), the composer and
// its upload input live in shadow roots (no ref for file_upload), and the page's
// CSP blocks fetching the image. So:
//
//   await li.openComposer()                    -> {editor:true}
//   await li.openMediaEditor()                 -> {uploadInput:true}
//   li.addProxyInput()                         then: find "Publishing proxy file input"
//                                              -> file_upload(cover.jpg, ref)
//   await li.moveProxyFileToEditor(110091)     -> {preview:"1200x627", nextEnabled:true}
//   await li.next()                            -> {composer:true, imageAttached:true}
//   await li.insertPost(TEXT)                  -> {inserted:true}
//   li.verifyPost(TEXT)                        -> {normalizedEqual:true, imageAttached:true}
//   await li.post()     ONLY when the author said to post in this session
//                                              -> {toast, url}
//
// Every helper refuses ({refused: ...}) instead of acting when its precondition
// fails; a guard inside one script is a real guard, unlike one inside a batch.

window.li = (() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const visible = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const deepAll = (root, sel, out = []) => {
    out.push(...root.querySelectorAll(sel));
    for (const el of root.querySelectorAll("*")) if (el.shadowRoot) deepAll(el.shadowRoot, sel, out);
    return out;
  };
  const label = (b) => (b.getAttribute("aria-label") || b.innerText || "").trim();
  const button = (name) => deepAll(document, "button,[role=button]").filter(visible).find((b) => label(b) === name);
  const editor = () => deepAll(document, '.ql-editor[contenteditable="true"]').find(visible) || null;
  const dialog = () => deepAll(document, "[role=dialog]").filter(visible)[0] || null;
  const uploadInput = () => deepAll(document, "input[type=file]").find((i) => i.id === "media-editor-file-selector__file-input") || null;
  const attachedImage = () => { const d = dialog(); return !!d && deepAll(d, "img").filter(visible).some((im) => im.naturalWidth >= 600); };

  // A ref click is swallowed in a hidden tab; this sequence is what React acted on.
  const press = (el) => {
    for (const t of ["pointerdown", "mousedown", "pointerup", "mouseup"])
      el.dispatchEvent(new (t.startsWith("pointer") ? PointerEvent : MouseEvent)(t, { bubbles: true, cancelable: true, button: 0 }));
    el.click();
  };

  async function openComposer() {
    if (editor()) return { editor: true, already: true };
    const b = deepAll(document, "button,[role=button]").filter(visible).find((x) => /start a post/i.test(label(x)));
    if (!b) return { refused: "no Start a post button (signed out, or not on the feed)" };
    press(b);
    for (let i = 0; i < 15 && !editor(); i++) await sleep(700);
    return { editor: !!editor(), empty: editor() ? editor().innerText.trim().length === 0 : null };
  }

  async function openMediaEditor() {
    if (uploadInput()) return { uploadInput: true, already: true };
    const b = button("Add media");
    if (!b) return { refused: "no Add media button (composer not open?)" };
    press(b);
    for (let i = 0; i < 10 && !uploadInput(); i++) await sleep(500);
    return { uploadInput: !!uploadInput() };
  }

  // find() and read_page cannot see into shadow roots, so give file_upload a target
  // in the light DOM.
  function addProxyInput() {
    let p = document.getElementById("publishing-proxy-file-input");
    if (!p) {
      p = document.createElement("input");
      p.type = "file"; p.id = "publishing-proxy-file-input"; p.accept = "image/jpeg,image/png,image/webp";
      p.setAttribute("aria-label", "Publishing proxy file input");
      Object.assign(p.style, { position: "fixed", top: "4px", left: "4px", zIndex: "2147483647", width: "220px", height: "28px", background: "#fff" });
      document.body.appendChild(p);
    }
    return { proxy: true, next: 'find "Publishing proxy file input", then upload the image to that input' };
  }

  async function moveProxyFileToEditor(expectedBytes) {
    const p = document.getElementById("publishing-proxy-file-input");
    const f = p && p.files && p.files[0];
    if (!f) return { refused: "proxy input holds no file; run file_upload first" };
    if (expectedBytes && f.size !== expectedBytes) return { refused: "size mismatch", size: f.size, expectedBytes };
    const target = uploadInput();
    if (!target) return { refused: "LinkedIn upload input not found; run openMediaEditor()" };
    const dt = new DataTransfer(); dt.items.add(f); target.files = dt.files;
    target.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
    target.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
    let img = null;
    for (let i = 0; i < 12 && !img; i++) {
      await sleep(800);
      img = deepAll(document, "img").filter(visible).find((im) => im.naturalWidth >= 600 && /^(blob:|data:)/.test(im.src));
    }
    p.remove();
    const n = button("Next");
    return { name: f.name, size: f.size, preview: img ? `${img.naturalWidth}x${img.naturalHeight}` : null,
             nextEnabled: n ? !(n.disabled || n.getAttribute("aria-disabled") === "true") : null, proxyRemoved: true };
  }

  async function next() {
    const n = button("Next");
    if (!n) return { refused: "no Next button" };
    press(n);
    for (let i = 0; i < 15 && !editor(); i++) await sleep(700);
    return { composer: !!editor(), imageAttached: attachedImage() };
  }

  // A synthetic paste leaves the composer at 1 character; insertText works.
  async function insertPost(text) {
    const ed = editor();
    if (!ed) return { refused: "composer editor not found" };
    if (ed.innerText.trim().length > 0) return { refused: "editor not empty", len: ed.innerText.trim().length };
    ed.focus();
    const r = document.createRange(); r.selectNodeContents(ed);
    const s = document.getSelection(); s.removeAllRanges(); s.addRange(r);
    const ok = document.execCommand("insertText", false, text);
    await sleep(1500);
    return { inserted: ok };
  }

  // Raw innerText length differs (blank lines are empty <p>); compare collapsed.
  function verifyPost(text) {
    const ed = editor();
    if (!ed) return { refused: "composer editor not found" };
    const norm = (s) => s.replace(/\s+/g, " ").trim();
    const a = norm(text), b = norm(ed.innerText);
    let firstDiff = -1;
    for (let i = 0; i < Math.max(a.length, b.length); i++) if (a[i] !== b[i]) { firstDiff = i; break; }
    const p = button("Post");
    return { normalizedEqual: a === b, sourceLen: a.length, editorLen: b.length, firstDiff,
             around: firstDiff >= 0 ? { source: a.slice(firstDiff - 15, firstDiff + 15), editor: b.slice(firstDiff - 15, firstDiff + 15) } : null,
             imageAttached: attachedImage(), postEnabled: p ? !(p.disabled || p.getAttribute("aria-disabled") === "true") : null };
  }

  // Publishes. The toast's "View post" link is the only place the URL shows up.
  async function post() {
    const p = button("Post");
    if (!p || p.disabled || p.getAttribute("aria-disabled") === "true") return { refused: "no enabled Post button" };
    press(p);
    let url = null, toast = "";
    for (let i = 0; i < 25; i++) {
      await sleep(1000);
      const link = deepAll(document, "a").filter(visible).find((a) => /\/feed\/update\/urn:li:(share|activity|ugcPost):/.test(a.getAttribute("href") || ""));
      if (link) url = link.href;
      toast = deepAll(document, "[role=alert],[role=status],.artdeco-toast-item").filter(visible).map((t) => t.innerText.replace(/\s+/g, " ").trim()).join(" | ");
      if (!editor() && url) break;
    }
    return { composerClosed: !editor(), toast: toast.slice(0, 120), url };
  }

  return { deepAll, press, openComposer, openMediaEditor, addProxyInput, moveProxyFileToEditor, next, insertPost, verifyPost, post };
})();
Object.keys(window.li);
