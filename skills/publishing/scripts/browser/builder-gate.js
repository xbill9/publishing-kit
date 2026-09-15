// AWS Builder Center publish gate: capture which links it actually rejected.
//
// MEASURED 2026-09-15. Publish POSTs api.builder.aws.com/cs/v2/content/submit-review
// and then polls .../review-status. Both responses carry
// contentIssues.{brokenLinks,maliciousLinks,profanityDetection}.violatedFragments --
// the exact offending URLs -- but the UI throws them away and shows only
// "A URL link you have shared is broken" / "...violates our AWS Builder Terms",
// each rendered twice. Guessing from those messages cost a full failed round.
//
// Use on the draft's /preview/content/<id>?v=<v> page:
//   1. paste this file (installs the hook, defines window.gate)
//   2. click Publish ONLY when the draft is known to fail -- a passing gate
//      publishes on its own
//   3. `await gate.wait()` then `gate.verdict()`
//
// javascript_tool redacts values that look like query strings or keys, so
// verdict() returns URLs as-is but never the raw body.

window.gate = (() => {
  const seen = [];
  const keep = (url, text) => {
    if (!/submit-review|review-status/.test(String(url))) return;
    try { seen.push({ url: String(url).split("?")[0], body: JSON.parse(text) }); } catch (e) { /* non-JSON poll tick */ }
  };
  if (!window.__gateHooked) {
    window.__gateHooked = true;
    const f = window.fetch;
    window.fetch = async (...a) => { const r = await f(...a); r.clone().text().then((t) => keep(a[0]?.url || a[0], t)).catch(() => {}); return r; };
    const o = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function (m, u, ...rest) {
      this.addEventListener("load", () => { try { keep(u, this.responseText); } catch (e) {} });
      return o.call(this, m, u, ...rest);
    };
  }

  async function wait(seconds = 25) {
    for (let i = 0; i < seconds && !seen.some((s) => s.body?.contentIssues); i++) await new Promise((r) => setTimeout(r, 1000));
    return seen.length;
  }

  // The last response wins: review-status is the settled verdict.
  function verdict() {
    const last = [...seen].reverse().find((s) => s.body?.contentIssues);
    if (!last) return { captured: false, responses: seen.map((s) => s.url) };
    const ci = last.body.contentIssues;
    const frag = (k) => ci[k]?.violatedFragments || [];
    return {
      captured: true,
      from: last.url,
      reviewStatus: last.body.reviewStatus,
      brokenLinks: frag("brokenLinks"),
      maliciousLinks: frag("maliciousLinks"),
      profanity: frag("profanityDetection"),
      titleRecommendation: ci.titleRecommendation,
      descriptionRecommendation: ci.descriptionRecommendation,
    };
  }

  return { wait, verdict, responses: () => seen.length };
})();
"gate hook installed";
