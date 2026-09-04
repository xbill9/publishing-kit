#!/usr/bin/env python3
"""Serve an article body over localhost so a browser can copy it.

This exists because getting ~15 KB of markdown into a rich-text `contenteditable`
is harder than it looks, and three obvious routes are closed:

  * cross-origin `fetch` of the raw markdown from the page -- blocked by CSP
  * the system clipboard from a shell (`wl-copy`, `xclip`) -- both hang holding
    the selection and time the command out, even detached with setsid/nohup
  * hand-transcribed base64 through a JS bridge -- MEASURED failure: a 3,192
    character chunk arrived as 3,152. Base64 has no redundancy, so a dropped
    character fails the decode outright.

What works is `http://127.0.0.1` -- `file://` is blocked by the Chrome extension
-- carried into the editor through `window.name`, which survives a cross-origin
navigation. NO CLIPBOARD:

    1. python3 serve-body.py article.md
    2. navigate the tab to the printed URL
    3. window.name = document.body.innerText   (checksum it; see SKILL.md)
    4. navigate the same tab to the editor and paste window.name through the
       JS bridge in references/browser-publishing.md

Do NOT drive this with Ctrl+A/Ctrl+C/Ctrl+V, which earlier revisions of this
docstring suggested. It overwrites the user's system clipboard -- and MEASURED
2026-09-04, a Ctrl+C that silently failed to take meant the following Ctrl+V
pasted the user's existing clipboard contents into their draft, where it
autosaved. `references/browser-publishing.md` says never to use the clipboard;
that is the rule.

Zero transcription, and the markdown converts properly on paste -- headings, real
tables, line-numbered code blocks.

The title and any `*Subtitle:*` line are stripped, because those are separate
fields in the editor. Note the off-by-one that makes `sed '1,2d'` wrong here: line
2 is usually the blank line after the title, so the subtitle survives it.

Ctrl-C to stop, or stop the background task that started it.
"""

import argparse
import hashlib
import http.server
import pathlib
import socketserver
import sys

from bodytext import unwrap


def strip_front(text: str) -> str:
    keep = [ln for ln in text.splitlines()
            if not (ln.startswith("# ") or ln.startswith("*Subtitle:"))]
    return "\n".join(keep).lstrip("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--port", type=int, default=8899)
    ap.add_argument("--keep-title", action="store_true",
                    help="do not strip the H1 and subtitle")
    ap.add_argument("--no-unwrap", action="store_true",
                    help="keep hard-wrapped lines (Builder Center will render them "
                         "as real line breaks -- almost never what you want)")
    a = ap.parse_args()

    src = pathlib.Path(a.article)
    text = src.read_text()
    body = text if a.keep_title else strip_front(text)
    if not a.no_unwrap:
        body = unwrap(body)
    payload = body.encode()

    print(f"{src.name}: {len(payload)} bytes  sha256 {hashlib.sha256(payload).hexdigest()[:16]}")
    print(f"first line: {body.splitlines()[0][:70]}")
    print(f"last line : {body.splitlines()[-1][:70]}")
    print(f"\n  http://127.0.0.1:{a.port}/body.md\n")
    print("open that in a second tab, Ctrl+A Ctrl+C, then Ctrl+V into the editor")

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            # text/plain so the browser renders it verbatim rather than as HTML
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            # CORS, so the EDITOR'S page can fetch this directly. Without it the
            # browser refuses with a bare "Failed to fetch", which reads exactly
            # like a CSP block and sent me down a clipboard rabbit hole once.
            # This is what makes the injection fully automatic: no clipboard, no
            # transcription, no human.
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    try:
        socketserver.TCPServer(("127.0.0.1", a.port), H).serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
        return 0


if __name__ == "__main__":
    sys.exit(main())
