// LinkedIn article editor helpers (linkedin.com/article/new, /article/edit/<id>/).
// This is the long-form article, not the feed post: the post's composer has its
// own helper, linkedin-composer.js.
//
// MEASURED 2026-11-19 pasting this kit's own article. Why each helper exists is in
// references/linkedin-article.md. Short version: the body is a Tiptap/ProseMirror
// editor that takes a synthetic text/html paste and re-hosts its images, but the
// page's Trusted Types policy strips every tag from HTML parsed in the page, so
// the adapting happens on 127.0.0.1 BEFORE the navigation; and the saved draft
// keeps two heading levels and no inline code.
//
// The file runs on both origins. Evaluate its text in the page each time, with
// the capability that evaluates JavaScript: do not carry it in window.name and
// eval() it there. eval() ran on most loads of the editor and threw EvalError (no
// 'unsafe-eval' in script-src) on one.
//
//   (on 127.0.0.1, the -hosted.html open in the tab; evaluate this file, then)
//   await lia.stash()                     -> {html, images, links, headings, ...}
//   (navigate the SAME tab to https://www.linkedin.com/article/new/; evaluate this file)
//   await lia.paste()                     -> {pasted:true, id, images:[{urn, alt}]}
//   lia.setTitle(TITLE)                   -> {title}
//   lia.coverInput()                      then: find "Publishing proxy file input"
//                                         -> file_upload(<16:9 cover>, ref)
//   await lia.coverNext()                 -> {cover:true}
//   (reload the tab, evaluate this file again)
//   lia.audit()                           -> what the reload loaded, against the stash
//   await lia.clear(<article id>)         only to replace a body you pasted
//
// Publishing, ONLY when the author said to publish in this session. Open the
// modal with a real click on Next (a scripted click on it is untested), then:
//   lia.publishSettings()                 -> {audience, postText, button}  read them out
//   lia.publish({audience: "Anyone", postText: ""})   refuses on any mismatch
//   (the tab moves to /pulse/<slug>/?published=t; evaluate this file again)
//   lia.published()                       -> {url, editId, post}
//
// Every helper refuses ({refused: ...}) instead of acting when its precondition
// fails; a guard inside one script is a real guard, unlike one inside a batch.

window.lia = (() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const editorEl = () => document.querySelector('.ProseMirror[contenteditable="true"]');
  const articleId = () => (location.pathname.match(/\/article\/edit\/(\d+)/) || [])[1] || null;
  const onEditor = () => /(^|\.)linkedin\.com$/.test(location.hostname) && /^\/article\/(new|edit)\b/.test(location.pathname);
  const stashed = () => { try { const p = JSON.parse(window.name); return p && p.lia === 1 ? p : null; } catch (e) { return null; } };
  const norm = (u) => u.replace(/\/$/, "");
  const TITLE_MAX = 150; // the Title textarea's maxLength, MEASURED 2026-11-19

  // Runs on 127.0.0.1 with the -hosted.html from make-medium.py open in the tab.
  // MEASURED 2026-11-19: on linkedin.com, DOMParser returned a body with no
  // element children for a source holding 269 tags (a Trusted Types default
  // policy), so nothing here can run after the navigation.
  //   - the leading image is the cover Medium needs in the body; LinkedIn has a
  //     cover slot, so it goes (keepCover: true keeps it)
  //   - <code> inside a link is unwrapped: the code mark excludes every other
  //     mark, so the paste would keep the code and drop the link
  //   - every other inline <code> STAYS. The saved draft keeps no code mark (40
  //     before a reload, 0 after), but with all 40 unwrapped the paste linked
  //     file names as URLs (make-medium.py -> http://make-medium.py, 41 link
  //     marks for 4 real targets). Under the mark nothing is linked, and the
  //     reload leaves plain text.
  //   - only heading levels 2 and 3 are saved; levels 1, 4, 5 and 6 reloaded as
  //     paragraphs. The largest heading in the source becomes h2, the rest h3.
  //     The paste itself lands every heading at level 3, so paste() sets them.
  async function stash({ keepCover = false } = {}) {
    if (!/^(127\.0\.0\.1|localhost)$/.test(location.hostname))
      return { refused: "stash() adapts the HTML and must run on 127.0.0.1, before navigating to LinkedIn" };
    // MEASURED 2026-11-19: with a plain fetch the tab's HTTP cache answered, and a
    // rebuilt article went in as its previous version, with every count agreeing
    // with the (equally stale) stash. no-store reads the file the server has now.
    const src = await (await fetch(location.href, { cache: "no-store" })).text();
    const doc = new DOMParser().parseFromString(src, "text/html");
    if (!doc.body.children.length) return { refused: "the page parsed to no elements" };
    doc.querySelectorAll("header, h1.title, style, script, link, meta, title").forEach((e) => e.remove());

    let coverDropped = null;
    const firstImg = doc.body.querySelector("img");
    if (firstImg && !keepCover) {
      const before = doc.createRange();
      before.setStart(doc.body, 0); before.setEndBefore(firstImg);
      if (!before.toString().trim()) {
        coverDropped = firstImg.getAttribute("src");
        (firstImg.closest("figure") || (firstImg.parentElement.children.length === 1 && firstImg.parentElement !== doc.body ? firstImg.parentElement : firstImg)).remove();
      }
    }

    let inlineCode = 0, codeLinks = 0;
    for (const c of [...doc.querySelectorAll("code")]) {
      if (c.closest("pre")) continue;
      if (c.closest("a[href]")) { c.replaceWith(...c.childNodes); codeLinks++; } else inlineCode++;
    }

    const hs = [...doc.querySelectorAll("h1,h2,h3,h4,h5,h6")];
    const top = hs.map((h) => +h.tagName[1]).sort()[0];
    const headings = { h2: 0, h3: 0 }, headingLevels = [];
    for (const h of hs) {
      const tag = +h.tagName[1] === top ? "h2" : "h3";
      const n = doc.createElement(tag);
      n.append(...h.childNodes); h.replaceWith(n); headings[tag]++; headingLevels.push(+tag[1]);
    }
    for (const e of doc.querySelectorAll("pre, pre code")) e.removeAttribute("class");

    // MEASURED 2026-11-19 with a probe paste. The schema's blockquote and listItem
    // each hold exactly one paragraph: a two-paragraph quote kept the first and
    // DROPPED the second, and a nested list ran into its parent item as
    // "outer oneinner oneinner two". So a quote is split into one per paragraph
    // and nested items are moved up behind their parent. A <table> pasted as one
    // paragraph of joined cells ("ABc1c2"); make-medium.py has already drawn
    // tables as images, so one here is counted and reported, never pasted blind.
    let quotesSplit = 0, nestedItems = 0;
    for (const q of [...doc.querySelectorAll("blockquote")]) {
      const kids = [...q.children];
      if (kids.length < 2) continue;
      for (const k of kids) { const n = doc.createElement("blockquote"); n.append(k); q.before(n); }
      q.remove(); quotesSplit++;
    }
    for (let inner; (inner = doc.querySelector("li ul, li ol")); ) {
      const parent = inner.closest("li");
      const items = [...inner.children].filter((c) => c.tagName === "LI");
      parent.after(...items); inner.remove(); nestedItems += items.length;
    }

    const expect = {
      links: [...new Set([...doc.querySelectorAll("a[href]")].map((a) => a.getAttribute("href")).filter((u) => /^https?:/.test(u)).map(norm))],
      alts: [...doc.querySelectorAll("img")].map((i) => i.getAttribute("alt") || ""),
      codeBlockLines: [...doc.querySelectorAll("pre")].map((p) => p.textContent.replace(/\n$/, "").split("\n").length),
      headings, headingLevels,
      listItems: doc.querySelectorAll("li").length,
      blockquotes: doc.querySelectorAll("blockquote").length,
      tables: doc.querySelectorAll("table").length,
      inkChars: doc.body.textContent.replace(/\s+/g, "").length,
    };
    const html = doc.body.innerHTML;
    window.name = JSON.stringify({ lia: 1, html, expect });
    return { html: html.length, carried: window.name.length, first: doc.body.textContent.trim().slice(0, 60), coverDropped, inlineCode, codeLinksUnwrapped: codeLinks, quotesSplit, nestedItemsHoisted: nestedItems, images: expect.alts.length, ...expect };
  }

  // The reading every other helper is built on: the editor's own document.
  function read() {
    const ed = editorEl();
    if (!ed || !ed.editor) return null;
    const j = ed.editor.getJSON();
    const types = {}, links = new Set(), codeBlockLines = [], images = [];
    const text = (n) => n.text || (n.content || []).map(text).join("");
    const walk = (n) => {
      types[n.type] = (types[n.type] || 0) + 1;
      for (const m of n.marks || []) { types["mark:" + m.type] = (types["mark:" + m.type] || 0) + 1; if (m.type === "link") links.add(norm(m.attrs.href)); }
      if (n.type === "codeBlock") codeBlockLines.push(text(n).split("\n").length);
      if (n.type === "heading") types["h" + n.attrs.level] = (types["h" + n.attrs.level] || 0) + 1;
      if (n.type === "inlineImage") images.push({ rehosted: /(^|\.)licdn\.com$/.test((() => { try { return new URL(n.attrs.src).hostname; } catch (e) { return ""; } })()), urn: n.attrs.urn || null, alt: n.attrs.alt || "" });
      (n.content || []).forEach(walk);
    };
    walk(j);
    const blocks = (j.content || []).filter((n) => text(n).trim() || n.type !== "paragraph");
    return { types, links: [...links], codeBlockLines, images, inkChars: text(j).replace(/\s+/g, "").length, first: text(blocks[0] || {}).slice(0, 80), last: text(blocks.at(-1) || {}).slice(0, 80) };
  }

  const saveStatus = () => (document.body.innerText.match(/Draft - [^\n]*/) || [null])[0];

  // A synthetic paste of text/html only. MEASURED 2026-11-19: each <img> on
  // raw.githubusercontent.com became an inlineImage with a
  // urn:li:digitalmediaAsset, and after a reload its src was on media.licdn.com.
  // The paste leaves alt empty, and an alt set on the node was still there
  // after the reload, so the alts from the stash are written back in order.
  async function paste() {
    if (!onEditor()) return { refused: "not on linkedin.com/article/new or /article/edit/<id>/" };
    const ed = editorEl(), p = stashed();
    if (!ed || !ed.editor) return { refused: "no Tiptap editor on the page" };
    if (!p) return { refused: "window.name holds no stash; run lia.stash() on 127.0.0.1 in this tab first" };
    if (ed.innerText.trim().length > 0 || ed.querySelector("img"))
      return { refused: `editor holds ${ed.innerText.trim().length} chars; refusing to paste on top (lia.clear(<id>) first)` };
    ed.focus();
    const dt = new DataTransfer();
    dt.setData("text/html", p.html);
    // dispatchEvent returns false here: that is preventDefault, not refusal.
    ed.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
    let r = null;
    for (let i = 0; i < 40; i++) {
      await sleep(500);
      r = read();
      if (r.images.length === p.expect.alts.length && r.images.every((im) => im.urn) && !r.types.imagePlaceholder) break;
    }
    // setNodeMarkup keeps a node's size, so every position stays valid in one transaction.
    const E = ed.editor, tr = E.state.tr;
    let k = 0, h = 0;
    E.state.doc.descendants((n, pos) => {
      if (n.type.name === "inlineImage") tr.setNodeMarkup(pos, null, { ...n.attrs, alt: p.expect.alts[k++] || "" });
      if (n.type.name === "heading") { const level = p.expect.headingLevels[h++]; if (level && level !== n.attrs.level) tr.setNodeMarkup(pos, null, { ...n.attrs, level }); }
    });
    if (tr.docChanged) E.view.dispatch(tr);
    for (let i = 0; i < 20 && !articleId(); i++) await sleep(500);
    r = read();
    return { pasted: true, id: articleId(), chars: ed.innerText.length, images: r.images, uploadsPending: r.images.filter((im) => !im.urn).length + (r.types.imagePlaceholder || 0), status: saveStatus() };
  }

  function setTitle(title) {
    if (!onEditor()) return { refused: "not on the article editor" };
    if (!title || title.length > TITLE_MAX) return { refused: `title is ${title ? title.length : 0} chars; the field takes 1 to ${TITLE_MAX}` };
    const t = document.querySelector("#article-editor-headline__textarea") || [...document.querySelectorAll("textarea")].find((e) => e.placeholder === "Title");
    if (!t) return { refused: "Title textarea not found" };
    const set = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    t.focus(); set.call(t, title);
    t.dispatchEvent(new Event("input", { bubbles: true }));
    t.dispatchEvent(new Event("change", { bubbles: true }));
    t.blur();
    return { title: t.value };
  }

  // "Upload from computer" opens an "Add cover image or video" dialog and calls
  // input.click() on #media-editor-file-selector__file-input. The click is
  // patched for the one call so no native picker opens.
  // MEASURED 2026-11-19: a 1376x578 cover previewed as 1027x578, cropped to
  // 16:9; a 1200x675 file previewed whole. Upload the 16:9 cover.
  const coverSet = () => [...document.querySelectorAll("button")].some((b) => /remove the cover image/i.test(b.getAttribute("aria-label") || ""));
  const coverDialog = () => [...document.querySelectorAll("[role=dialog]")].find((d) => d.getClientRects().length && /Add cover image or video/.test(d.innerText)) || null;
  function coverInput() {
    if (!onEditor()) return { refused: "not on the article editor" };
    if (coverSet()) return { refused: "the article already has a cover; remove it in the editor first" };
    if (!coverDialog()) {
      const b = [...document.querySelectorAll("button")].find((x) => /^Upload from computer$/.test(x.innerText.trim()));
      if (!b) return { refused: "no Upload from computer button" };
      const orig = HTMLInputElement.prototype.click;
      HTMLInputElement.prototype.click = function () { if (this.type === "file") return; return orig.apply(this, arguments); };
      try { b.click(); } finally { HTMLInputElement.prototype.click = orig; }
    }
    const i = document.querySelector("#media-editor-file-selector__file-input") || (coverDialog() || document).querySelector("input[type=file]");
    if (!i) return { refused: "the dialog opened without a file input; read it again in a second script" };
    i.setAttribute("aria-label", "Publishing proxy file input");
    return { input: true, accept: i.accept };
  }

  async function coverNext() {
    const d = coverDialog();
    if (!d) return { refused: "the cover dialog is not open; lia.coverInput() and file_upload first" };
    const im = [...d.querySelectorAll("img")].find((x) => x.naturalWidth > 0);
    if (!im) return { refused: "no preview in the dialog; the file has not landed" };
    const preview = `${im.naturalWidth}x${im.naturalHeight}`;
    const next = [...d.querySelectorAll("button")].find((b) => b.innerText.trim() === "Next");
    if (!next || next.disabled) return { refused: "Next is missing or disabled", preview };
    next.click();
    for (let i = 0; i < 30 && !coverSet(); i++) await sleep(500);
    return { cover: coverSet(), preview, status: saveStatus() };
  }

  // What the editor holds now, against what stash() sent. After a RELOAD this is
  // the saved draft: the editor's document is then what LinkedIn stored.
  function audit() {
    if (!onEditor()) return { refused: "not on the article editor" };
    const r = read();
    if (!r) return { refused: "no Tiptap editor on the page" };
    const p = stashed(), out = { id: articleId(), status: saveStatus(), cover: coverSet(), title: document.querySelector("#article-editor-headline__textarea")?.value ?? null, ...r };
    if (!p) return { ...out, compared: false };
    const e = p.expect, t = r.types, problems = [];
    const missingLinks = e.links.filter((u) => !r.links.includes(u));
    if (missingLinks.length) problems.push(`links missing: ${missingLinks.join(" ")}`);
    const addedLinks = r.links.filter((u) => !e.links.includes(u));
    if (addedLinks.length) problems.push(`links the source does not hold (the editor links bare names): ${addedLinks.join(" ")}`);
    if (String(r.codeBlockLines) !== String(e.codeBlockLines)) problems.push(`code blocks ${r.codeBlockLines} lines, sent ${e.codeBlockLines}`);
    if (r.images.length !== e.alts.length) problems.push(`${r.images.length} images, sent ${e.alts.length}`);
    if (r.images.some((im) => !im.urn)) problems.push("an image has no urn: its upload did not finish");
    if (String(r.images.map((im) => im.alt)) !== String(e.alts)) problems.push("image alt text differs from the source");
    for (const h of ["h2", "h3"]) if ((t[h] || 0) !== e.headings[h]) problems.push(`${t[h] || 0} ${h}, sent ${e.headings[h]}`);
    if ((t.listItem || 0) !== e.listItems) problems.push(`${t.listItem || 0} list items, sent ${e.listItems}`);
    if ((t.blockquote || 0) !== e.blockquotes) problems.push(`${t.blockquote || 0} blockquotes, sent ${e.blockquotes}`);
    // Every non-space character, so text the editor drops shows up whatever dropped it.
    if (r.inkChars !== e.inkChars) problems.push(`${r.inkChars} non-space characters, sent ${e.inkChars}`);
    if (e.tables) problems.push(`the source held ${e.tables} <table>; the editor has no table node`);
    if (t.imagePlaceholder) problems.push(`${t.imagePlaceholder} image placeholder(s) still uploading`);
    return { ...out, compared: true, problems };
  }

  // Replacing a body: clear through the editor's own command, never by pasting
  // over a selection. Takes the article id so it cannot clear the wrong draft.
  async function clear(id) {
    if (!id || String(id) !== articleId()) return { refused: `pass this article's id (${articleId()}) to confirm` };
    const ed = editorEl();
    if (!ed || !ed.editor) return { refused: "no Tiptap editor on the page" };
    ed.editor.commands.clearContent(true);
    await sleep(1500);
    return { cleared: true, chars: ed.innerText.trim().length, images: ed.querySelectorAll("img").length };
  }

  // Next opens a "Create post modal": a post box ("Tell your network what your
  // article is about…"), the audience, Schedule post and Publish.
  // MEASURED 2026-11-19: Publish was enabled with the post box empty, and one
  // scripted click on it published the article and moved the tab to
  // /pulse/<slug>/?published=t within four seconds. The click runs after this
  // returns, because that navigation ends any script still in the page.
  const postModal = () => [...document.querySelectorAll("[role=dialog]")].find((d) => d.getClientRects().length && /Create post modal/.test(d.innerText)) || null;
  function publishSettings() {
    const d = postModal();
    if (!d) return null;
    const labels = [...d.querySelectorAll("button")].map((b) => b.innerText.trim().replace(/\s+/g, " "));
    const box = d.querySelector('[contenteditable="true"]');
    const go = [...d.querySelectorAll("button")].find((b) => b.innerText.trim() === "Publish");
    return { audience: ((labels.find((t) => /Post to /.test(t)) || "").match(/Post to (.*)$/) || [])[1] || null, postText: box ? box.innerText.trim() : null, button: go ? (go.disabled ? "Publish (disabled)" : "Publish") : null };
  }
  function publish(expect) {
    const s = publishSettings();
    if (!s) return { refused: "the Create post modal is not open; click Next in the editor first and read lia.publishSettings()" };
    if (!expect || typeof expect.audience !== "string" || typeof expect.postText !== "string")
      return { refused: "pass {audience, postText} as read out to the author; publishing cannot be undone from here", settings: s };
    for (const k of ["audience", "postText"])
      if (expect[k] !== s[k]) return { refused: `${k} is ${JSON.stringify(s[k])}, expected ${JSON.stringify(expect[k])}`, settings: s };
    if (s.button !== "Publish") return { refused: `the button reads ${s.button}`, settings: s };
    const go = [...postModal().querySelectorAll("button")].find((b) => b.innerText.trim() === "Publish");
    setTimeout(() => go.click(), 100);
    return { clicked: "Publish", settings: s };
  }

  // On the published page. The slug is LinkedIn's: "Streamline Publishing with a
  // Claude Code Skill" became streamline-publishing-claude-code-skill-<author>-<5
  // characters>, so take the URL from here, never from the title.
  function published() {
    if (!/^\/pulse\/[^/]+\/?$/.test(location.pathname) || /^\/pulse\/draft\b/.test(location.pathname))
      return { published: false, refused: "not on a /pulse/<slug>/ page" };
    const href = (re) => [...document.querySelectorAll("a[href]")].map((a) => a.getAttribute("href")).find((h) => re.test(h)) || null;
    const edit = href(/^\/article\/edit\/\d+/), post = href(/^\/feed\/update\/urn:li:/);
    return { published: true, url: location.origin + location.pathname, editId: edit ? edit.match(/\d+/)[0] : null, post: post ? location.origin + post : null, title: document.title.replace(/^\(\d+\)\s*/, "").replace(/ \| LinkedIn$/, "") };
  }

  return { stash, paste, setTitle, coverInput, coverNext, audit, clear, publishSettings, publish, published };
})();
