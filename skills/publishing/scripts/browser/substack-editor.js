// Substack editor helpers, for evaluation in the page on
// <pub>.substack.com/publish/post/<id>.
//
// MEASURED 2026-10-05 pasting this kit's own article. Why each helper exists is in
// references/substack.md. Short version: the body is a tiptap/ProseMirror editor
// that takes a synthetic HTML paste, but its `code` mark excludes every other
// mark, so a link around inline code is dropped with no error; and the stored
// draft is readable as JSON from the same origin, so audit that, not the DOM.
//
//   (on 127.0.0.1, same tab)  window.name = await (await fetch(location.href)).text()
//   (navigate to the editor)
//   ss.prepare()                               -> {html, codeLinksUnwrapped, anchors}
//   await ss.paste()                           -> {pasted:true, chars}
//   ss.setTitle(TITLE, SUBTITLE)               -> {title, subtitle}
//   await ss.audit()                           -> counts from the SAVED draft
//   await ss.clear(<draft id>)                 only to replace a body you pasted
//
// There is no ss.publish. Publishing is the author's click.
//
// Every helper refuses ({refused: ...}) instead of acting when its precondition
// fails; a guard inside one script is a real guard, unlike one inside a batch.

window.ss = (() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const editor = () => document.querySelector('.ProseMirror[contenteditable="true"]');
  const draftId = () => (location.pathname.match(/\/publish\/post\/(\d+)/) || [])[1] || null;
  let prepared = null;

  // window.name holds the -hosted.html from make-medium.py. Title and subtitle are
  // their own fields, so the header goes. <a><code>x</code></a> becomes <a>x</a>:
  // the schema's code mark has excludes "_", and the paste keeps the code and
  // drops the link. make-medium.py demotes sections to <h4> because Medium has two
  // heading sizes; Substack has six, and h4 is 21px against 19px body text, so
  // sections go back up to `sectionHeading`.
  function prepare(src = window.name, { sectionHeading = "h3" } = {}) {
    if (!src || src.length < 200) return { refused: "window.name is empty; load the hosted HTML from 127.0.0.1 in this tab first" };
    const doc = new DOMParser().parseFromString(src, "text/html");
    doc.querySelectorAll("header, h1.title, style, script, link, meta").forEach((e) => e.remove());
    let codeLinksUnwrapped = 0;
    for (const a of doc.querySelectorAll("a[href]"))
      for (const c of a.querySelectorAll("code")) { c.replaceWith(...c.childNodes); codeLinksUnwrapped++; }
    for (const h of doc.querySelectorAll("h4")) {
      const n = doc.createElement(sectionHeading);
      n.append(...h.childNodes); h.replaceWith(n);
    }
    const anchors = [...doc.querySelectorAll("a[href]")].filter((a) => /^https?:/.test(a.getAttribute("href"))).length;
    prepared = { html: doc.body.innerHTML, text: doc.body.innerText };
    return { html: prepared.html.length, codeLinksUnwrapped, anchors, images: doc.querySelectorAll("img").length, pres: doc.querySelectorAll("pre").length };
  }

  async function paste() {
    const ed = editor();
    if (!ed) return { refused: "no editor; open <pub>.substack.com/publish/post/<id>" };
    if (!prepared) return { refused: "call ss.prepare() first" };
    if (ed.innerText.trim().length > 0) return { refused: `editor holds ${ed.innerText.trim().length} chars; refusing to paste on top (ss.clear(<id>) first)` };
    ed.focus();
    const dt = new DataTransfer();
    dt.setData("text/html", prepared.html);
    dt.setData("text/plain", prepared.text);
    // dispatchEvent returns false here: that is preventDefault, not refusal.
    ed.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
    await sleep(3000);
    return { pasted: true, chars: ed.innerText.length };
  }

  // The post's Title and subtitle are textareas in the editor, placeholders "Title"
  // and "Add a subtitle…". The "Add a title..." input and "Add a description..."
  // textarea are the SEO settings, a different pair.
  function setTitle(title, subtitle) {
    const t = [...document.querySelectorAll("textarea")].find((e) => e.placeholder === "Title");
    const s = [...document.querySelectorAll("textarea")].find((e) => /^Add a subtitle/.test(e.placeholder));
    if (!t || !s) return { refused: "post title/subtitle textareas not found" };
    const set = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    for (const [el, v] of [[t, title], [s, subtitle]]) {
      if (v == null) continue;
      el.focus(); set.call(el, v);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      el.blur();
    }
    return { title: t.value, subtitle: s.value };
  }

  // Read the draft as Substack stored it. Wait for the autosave first.
  async function audit(id = draftId()) {
    if (!id) return { refused: "no draft id in the URL" };
    await sleep(3000);
    const r = await fetch(`/api/v1/drafts/${id}`, { credentials: "include" });
    if (!r.ok) return { refused: `GET /api/v1/drafts/${id} -> ${r.status}` };
    const j = await r.json();
    const body = JSON.parse(j.draft_body || '{"type":"doc"}');
    const types = {}, links = new Set(), codeBlocks = [], images = [];
    const text = (n) => n.text || (n.content || []).map(text).join("");
    const walk = (n) => {
      types[n.type] = (types[n.type] || 0) + 1;
      for (const m of n.marks || []) { types["mark:" + m.type] = (types["mark:" + m.type] || 0) + 1; if (m.type === "link") links.add(m.attrs.href); }
      if (n.type === "code_block") codeBlocks.push(text(n).split("\n").length);
      if (n.type === "heading") types["h" + n.attrs.level] = (types["h" + n.attrs.level] || 0) + 1;
      if (n.type === "image2") images.push({ rehosted: /substack-post-media/.test(n.attrs.src), alt: n.attrs.alt, w: n.attrs.width });
      (n.content || []).forEach(walk);
    };
    walk(body);
    return {
      id, title: j.draft_title, subtitle: j.draft_subtitle, updated: j.draft_updated_at,
      types, links: [...links], codeBlockLines: codeBlocks, images,
      first: text(body.content?.[0] || {}).slice(0, 80), last: text(body.content?.at(-1) || {}).slice(0, 80),
    };
  }

  // Replacing a body: clear through the editor's own command, never by pasting
  // over a selection. Takes the draft id so it cannot clear the wrong draft.
  async function clear(id) {
    if (!id || String(id) !== draftId()) return { refused: `pass this draft's id (${draftId()}) to confirm` };
    const ed = editor();
    if (!ed?.editor) return { refused: "no tiptap editor instance on the ProseMirror element" };
    ed.editor.commands.clearContent(true);
    await sleep(1500);
    return { cleared: true, chars: ed.innerText.trim().length };
  }

  return { prepare, paste, setTitle, audit, clear };
})();
