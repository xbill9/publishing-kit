#!/usr/bin/env python3
"""Regressions the dogfood article cannot catch, because it never trips them.

The article exercises the happy path. Each test here is one input that shipped
wrong or was found wrong, with the failing input kept as the control. Stdlib only,
no network, no writes outside a temporary directory.

    python3 -m unittest discover -s tests -v
"""

import contextlib
import importlib.util
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "publishing" / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


import bodytext  # noqa: E402

facts, medium, builder, prose, links, devto = map(load, (
    "check-facts", "make-medium", "make-builder", "check-prose", "check-links",
    "publish-devto"))


def run(script, *args, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPTS / f"{script}.py"), *map(str, args)],
                          cwd=cwd, capture_output=True, text=True)


class Fences(unittest.TestCase):
    def kinds(self, *lines):
        return bodytext.fence_kinds(list(lines))

    def test_tilde(self):
        self.assertEqual(self.kinds("~~~", "x", "~~~", "y"), ["open", "body", "close", ""])

    def test_longer_fence_holds_a_shorter_one(self):
        self.assertEqual(self.kinds("````", "```", "x", "```", "````"),
                         ["open", "body", "body", "body", "close"])

    def test_other_marker_does_not_close(self):
        self.assertEqual(self.kinds("```", "~~~", "```"), ["open", "body", "close"])

    def test_unclosed_runs_to_the_end(self):
        self.assertEqual(self.kinds("```", "x"), ["open", "body"])

    def test_inline_triple_backticks_are_not_a_fence(self):
        self.assertEqual(self.kinds("```x```", "y"), ["", ""])


class Unwrap(unittest.TestCase):
    def same(self, text):
        self.assertEqual(bodytext.unwrap(text), text)

    def test_control_a_wrapped_paragraph_does_join(self):
        self.assertEqual(bodytext.unwrap("a\nb"), "a b")

    def test_tilde_fence(self):
        self.same("~~~\nline1\nline2\n~~~")

    def test_nested_fence(self):
        self.same("````\n```\nline1\nline2\n```\n````")

    def test_reference_definitions(self):
        self.same("[a]: http://x\n[b]: http://y")

    def test_paren_list(self):
        self.same("1) one\n2) two")

    def test_nested_quote(self):
        self.same("> > a\n> > b")

    def test_hard_break(self):
        self.assertEqual(bodytext.unwrap("a  \nb\nc"), "a  \nb c")

    def test_hard_wrapped_ignores_a_tilde_block(self):
        self.assertEqual(bodytext.hard_wrapped("~~~\na\nb\n~~~\n"), [])

    def test_hard_wrapped_control(self):
        self.assertEqual(len(bodytext.hard_wrapped("a\nb\n")), 1)


class Facts(unittest.TestCase):
    def traced(self, claim, evidence):
        return facts.key(facts.numbers(claim)) in facts.key(facts.numbers(evidence))

    def test_numbers_do_not_run_together(self):
        self.assertFalse(self.traced("123.4 ms", "latency 12 then 3.4 ms"))
        self.assertFalse(self.traced("47 of 62", "rows 147 and 629"))
        self.assertFalse(self.traced("4.35 s", "4.355"))

    def test_control_real_matches_still_trace(self):
        self.assertTrue(self.traced("15,360 MiB", "memory 15360"))
        self.assertTrue(self.traced("47 of 62", "47 / 62 paragraphs"))
        self.assertTrue(self.traced("v0.26.0", "version 0.26.0"))

    def test_binary_evidence_is_not_read(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t)
            (d / "a.bin").write_bytes(b"\xff\xfe 123.4 \x00")
            (d / "b.txt").write_text("ok 1")
            self.assertEqual([f.name for f, *_ in facts.load_evidence([d])], ["b.txt"])


class Medium(unittest.TestCase):
    def cells(self, cell):
        return [(t, b, i) for t, b, _, i in medium.runs(cell)]

    def plain(self, cell):
        self.assertEqual("".join(t for t, *_ in medium.runs(cell)), cell)
        self.assertFalse(any(b or m or i for _, b, m, i in medium.runs(cell)))

    def test_literal_delimiters(self):
        for c in ("4 * 1024 * 1024", "a _ b _ c", "Q5_K_M", "é_x_é", "* 1024 *"):
            self.plain(c)

    def test_control_real_emphasis(self):
        self.assertEqual(self.cells("*x*"), [("x", False, True)])
        self.assertEqual(self.cells("_x_"), [("x", False, True)])
        self.assertEqual(self.cells("__init__"), [("init", True, False)])
        self.assertEqual(self.cells("**x**"), [("x", True, False)])

    def test_escaped_pipe(self):
        hdr, body = medium.parse_table(["| a | b |", "| - | - |", r"| x \| y | 2 |"])
        self.assertEqual(hdr, ["a", "b"])
        self.assertEqual(body, [["x | y", "2"]])

    def test_data_row_of_dashes_survives(self):
        _, body = medium.parse_table(["| a |", "|---|", "| - |"])
        self.assertEqual(body, [["-"]])

    def test_headings(self):
        keep = ["#1 in the ranking", "#gemma #ai", "##nospace"]
        self.assertEqual(medium.demote_headings(keep), keep)
        self.assertEqual(medium.demote_headings(["~~~", "# c", "~~~"]), ["~~~", "# c", "~~~"])
        self.assertEqual(medium.demote_headings(["# T", "## S", "p", "# Later"]),
                         ["#### S", "p", "#### Later"])

    def test_hosted_has_no_relative_images(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t)
            from PIL import Image
            Image.new("RGB", (4, 4)).save(d / "shot.png")
            (d / "a.md").write_text("---\ntitle: T\n---\n\nHi\n\n![s](shot.png)\n")
            with contextlib.redirect_stdout(io.StringIO()):
                medium.convert(d / "a.md", d / "medium", "https://x.invalid/")
            html = (d / "medium" / "a-hosted.html").read_text()
            self.assertIn('src="https://x.invalid/shot.png"', html)
            self.assertTrue((d / "medium" / "img" / "shot.png").exists())

    def test_cover_comes_from_front_matter(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t)
            (d / "cover.aaaa.jpg").write_bytes(b"old")
            (d / "cover.zzzz.jpg").write_bytes(b"new")
            (d / "a.md").write_text("---\ncover_image: https://x/cover.zzzz.jpg\n---\n")
            self.assertEqual(medium.default_cover(d / "a.md").name, "cover.zzzz.jpg")

    def test_help(self):
        self.assertEqual(run("make-medium", "--help").returncode, 0)
        self.assertEqual(run("make-medium", "-h").returncode, 0)


class Freshness(unittest.TestCase):
    """check-article, against a real git repo, with the two holes as controls."""

    ARTICLE = ("---\ntitle: T\npublished: false\ndescription: D\ntags: a\n"
               "cover_image: https://x.invalid/{cover}\n---\n\nHello there.\n\n"
               "| a | b |\n| --- | --- |\n| 1 | {cell} |\n")

    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.d = d = pathlib.Path(self.t.name)
        from PIL import Image
        Image.new("RGB", (1376, 578), "white").save(d / "cover.aaaa.jpg")
        Image.new("RGB", (1376, 578), "red").save(d / "cover.zzzz.jpg")
        (d / "a.md").write_text(self.ARTICLE.format(cover="cover.zzzz.jpg", cell="100 ms"))
        self.git("init", "-q")
        self.build()

    def git(self, *a):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a],
                       cwd=self.d, check=True, capture_output=True)

    def build(self, *extra):
        subprocess.run([sys.executable, str(SCRIPTS / "make-medium.py"), "a.md", "medium",
                        "--img-base=https://x.invalid/medium/img/", *extra],
                       cwd=self.d, check=True, capture_output=True)
        self.git("add", "-A")
        self.git("commit", "-qm", "x", "--allow-empty")

    def check(self):
        return run("check-article", self.d / "a.md").stdout

    def test_control_fresh_passes(self):
        self.assertIn("matches a fresh build", self.check())

    def test_changed_table_cell_is_stale(self):
        (self.d / "a.md").write_text(self.ARTICLE.format(cover="cover.zzzz.jpg", cell="999 ms"))
        self.assertIn("draws different image", self.check())

    def test_wrong_cover_is_stale(self):
        self.build("--cover=cover.aaaa.jpg")
        self.assertIn("is stale", self.check())

    def test_relative_image_fails(self):
        h = self.d / "medium" / "a-hosted.html"
        h.write_text(h.read_text().replace("</body>", '<img src="s.png" /></body>'))
        self.assertIn("relative image", self.check())


class Builder(unittest.TestCase):
    def test_wrapped_disclaimer(self):
        wrapped = builder.DISCLAIMER.replace("author ", "author\n")
        self.assertNotIn("opinions", builder.convert(f"Body.\n\n*{wrapped}*\n", "T", ""))

    def test_tilde_block_is_not_a_table(self):
        self.assertEqual(builder.widest_table("~~~\n| a | b | c |\n~~~\n"), 0)


class Prose(unittest.TestCase):
    def test_a_phrase_split_by_a_wrap_is_found(self):
        got = prose.paragraphs("---\ntitle: x\n---\n\nThis is the\nfirst line.\n")
        body = [t for t, spans in got if spans[0][0] == 0 and "first" in t]
        self.assertEqual(body, ["This is the first line."])

    def test_control_a_list_item_does_not_join(self):
        self.assertEqual(len(prose.paragraphs("- one\n- two\n")), 2)


class Links(unittest.TestCase):
    def test_any_branch_maps_to_disk(self):
        d = pathlib.Path("/r/art")
        for ref in ("main", "master", "a" * 40):
            u = f"https://raw.githubusercontent.com/u/r/{ref}/art/img/x.png"
            self.assertEqual(links.local_for(u, d), d / "img/x.png")

    def test_parentheses_stay_in_the_url(self):
        u = "https://en.wikipedia.org/wiki/Foo_(bar)"
        self.assertEqual(links.MD_LINK.findall(f"[x]({u})"), [u])
        self.assertEqual(links.NAIVE_URL.findall(f"see {u}"), [u])


class Announce(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.d = pathlib.Path(self.t.name)
        (self.d / "a.md").write_text("---\ntitle: T\ndescription: D\n---\n\nHello.\n\n~~~\ncode here\n~~~\n")

    def test_gchat_honours_skip(self):
        (self.d / "links.txt").write_text("devto-gde = PENDING\nmedium = SKIP\n")
        run("make-gchat", self.d / "a.md")
        post = (self.d / "gchat-a.txt").read_text()
        self.assertNotIn("SKIP", post)
        self.assertNotIn("code here", post)

    def test_advocu_skip_falls_back(self):
        (self.d / "links.txt").write_text("devto-gde = SKIP\ndevto = https://localhost:1/x\n")
        run("make-advocu", self.d / "a.md", "--no-cover", "--date", "2026-01-01")
        sheet = (self.d / "advocu-a.md").read_text()
        self.assertIn("https://localhost:1/x", sheet)
        self.assertNotIn("SKIP", sheet)


class DevtoUpdate(unittest.TestCase):
    """The API is faked: a real run would touch a live article."""

    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.art = pathlib.Path(self.t.name) / "a.md"
        self.art.write_text("---\ntitle: T\npublished: false\n---\n\nBody\npublished: false\n")
        self.puts = []
        devto.preflight = lambda *a: None

    def go(self, *argv, live=(1,), draft=(2,), lost=False, orgs=True):
        def call(method, path, payload=None):
            if method == "PUT":
                self.puts.append(payload)
                return 200, {"id": 1, "title": "T", "published": True}
            if method == "POST":
                self.puts.append(payload)
                return 201, {"id": 9, "title": "T"}
            if path.startswith("/organizations/"):
                return (200, {"id": 5}) if orgs else (404, {})
            ids = draft if "unpublished" in path else ([] if lost and self.puts else live)
            return 200, [{"id": i} for i in ids]
        devto.call = call
        sys.argv = ["publish-devto", *argv]
        with contextlib.redirect_stdout(io.StringIO()):
            return devto.main()

    def sent(self):
        return self.puts[-1]["article"]["body_markdown"]

    def test_live_article_stays_live(self):
        self.go("--update", "1", str(self.art))
        self.assertIn("published: true", self.sent().split("---")[1])
        self.assertIn("published: false", self.sent().split("---")[2], "body line left alone")

    def test_control_draft_stays_draft(self):
        self.go("--update", "2", str(self.art))
        self.assertIn("published: false", self.sent().split("---")[1])

    def test_unknown_id_refuses(self):
        with self.assertRaises(SystemExit):
            self.go("--update", "3", str(self.art))
        self.assertEqual(self.puts, [])

    def test_leaving_the_listing_fails(self):
        with self.assertRaises(SystemExit):
            self.go("--update", "1", str(self.art), lost=True)

    def test_unknown_org_stops_before_create(self):
        with self.assertRaises(SystemExit):
            self.go("--create", str(self.art), "--org-slug", "nope", orgs=False)
        self.assertEqual(self.puts, [])




class BrowserHelpers(unittest.TestCase):
    def node(self, script):
        r = subprocess.run(["node", "-e", script], capture_output=True, text=True, cwd=SCRIPTS)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_gate_survives_a_second_paste(self):
        got = self.node("""
          const fs = require('fs'), vm = require('vm');
          const w = {fetch: async () => ({clone: () => ({text: async () =>
              JSON.stringify({contentIssues: {brokenLinks: {violatedFragments: ['u']}}})})})};
          w.window = w;
          class X { open() {} addEventListener() {} }
          w.XMLHttpRequest = X; w.setTimeout = setTimeout;
          const c = vm.createContext(w), src = fs.readFileSync('browser/builder-gate.js', 'utf8');
          vm.runInContext(src, c); vm.runInContext(src, c);
          w.fetch('https://a/submit-review').then(() => setTimeout(() =>
            console.log(JSON.stringify(w.gate.verdict())), 20));
        """)
        self.assertTrue(got["captured"])
        self.assertEqual(got["brokenLinks"], ["u"])

    def test_replace_body_refuses_before_clearing(self):
        src = (SCRIPTS / "browser" / "builder-editor.js").read_text()
        body = src[src.index("async function replaceBody"):]
        self.assertLess(body.index('"text is empty'), body.index("lx.update"))
        self.assertIn("setEditorState(prior)", body)


if __name__ == "__main__":
    unittest.main()
