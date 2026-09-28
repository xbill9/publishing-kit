// Kaggle benchmark page helpers, for evaluation in the page on
// kaggle.com/benchmarks/<owner>/<slug>.
//
// MEASURED 2026-09-28 writing a benchmark description. Why each helper exists is in
// references/kaggle.md. Short version: typing into the description textarea froze
// the tab, a ref click on the section's pencil only scrolled, and the section stays
// a draft unless its "Publish section" toggle is on when it is saved. So:
//
//   await kg.openDescription()          -> {editor:true}
//   await kg.setDescription(TEXT)        -> {set:true, length:N}
//   kg.publishToggle()                   -> {on:false}   click the toggle, then again -> {on:true}
//   (click Save, reload the page)
//   await kg.verifyDescription(TEXT)     -> {draft:false, startsWith:true}
//
// setDescription and openDescription package the in-page script that worked on
// 2026-09-28; this file as a whole has not yet been run end to end.
//
// Every helper refuses ({refused: ...}) instead of acting when its precondition
// fails; a guard inside one script is a real guard, unlike one inside a batch.

window.kg = (() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const visible = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const pencil = () => [...document.querySelectorAll("button")].find((b) => (b.getAttribute("aria-label") || "") === "Edit Description Section") || null;
  // The page held two textareas while the editor was open; the editor is the large visible one.
  const textarea = () => [...document.querySelectorAll("textarea")].filter(visible)
    .sort((a, b) => b.getBoundingClientRect().height - a.getBoundingClientRect().height)[0] || null;
  const toggleInput = () => {
    const lab = [...document.querySelectorAll("label,span,div")].filter(visible).find((x) => x.children.length === 0 && (x.innerText || "").trim() === "Publish section");
    if (!lab) return null;
    let box = lab;
    for (let i = 0; i < 4 && box; i++, box = box.parentElement) {
      const input = box.querySelector("input[type=checkbox],[role=switch]");
      if (input) return input;
    }
    return null;
  };

  async function openDescription() {
    if (textarea()) return { editor: true, already: true };
    const b = pencil();
    if (!b) return { refused: "no 'Edit Description Section' button; is this the benchmark's Leaderboard tab?" };
    b.scrollIntoView({ block: "center" });
    b.click();
    await sleep(1500);
    return textarea() ? { editor: true } : { refused: "clicked the pencil but no textarea appeared" };
  }

  // Native setter + input event: typing ~1,100 characters froze the tab.
  async function setDescription(text) {
    const ta = textarea();
    if (!ta) return { refused: "no description textarea; run openDescription() first" };
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    ta.focus();
    setter.call(ta, text);
    ta.dispatchEvent(new Event("input", { bubbles: true }));
    ta.dispatchEvent(new Event("change", { bubbles: true }));
    await sleep(300);
    return ta.value === text ? { set: true, length: ta.value.length } : { refused: "value did not stick", length: ta.value.length };
  }

  function publishToggle() {
    const t = toggleInput();
    if (!t) return { refused: "no 'Publish section' toggle found" };
    const on = t.getAttribute("aria-checked") === "true" || t.checked === true;
    return { on };
  }

  // After Save and a reload: the placeholder heading reads "Description (Draft)".
  async function verifyDescription(text) {
    await sleep(1000);
    const body = document.body.innerText;
    const i = body.indexOf("Description");
    if (i < 0) return { refused: "no Description section on the page" };
    const section = body.slice(i, i + 400);
    const first = text.replace(/\*\*/g, "").slice(0, 40);
    return { draft: /Description\s*\(Draft\)/.test(section), startsWith: section.includes(first) };
  }

  return { openDescription, setDescription, publishToggle, verifyDescription };
})();
