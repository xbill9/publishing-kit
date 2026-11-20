# LinkedIn articles, measured

This is the long-form **article** (`linkedin.com/article/new/`, published under
`/pulse/`), a different thing from the feed **post** that announces an article.
The post is `references/linkedin.md` and `scripts/browser/linkedin-composer.js`.
The article's helper is `scripts/browser/linkedin-article.js` (`window.lia`).

MEASURED 2026-11-19, all of it, by pasting this kit's own article
into a new article draft, in a visible tab, and reading the draft back after a
reload. **Nothing was published**: the route ends at a saved draft, and every
step after the `Publish` button is unmeasured.

**Correction.** That last sentence held for the first run only. Later the same
day the article was rebuilt, pasted again and published, and `Publish`, the
published URL and the public fetch are measured under "Publishing" below. What
is still unmeasured is listed at the end.

## How the article gets there

**Browser automation, pasting the same `-hosted.html` that `make-medium.py`
writes.** The editor has no table node, so the table images Medium needs are the
ones this editor needs. `lia.stash()` adapts the file on `127.0.0.1`, before the
tab goes to LinkedIn, so there is no `make-linkedin-article.py` to drift from it.

1. `python3 -m http.server 8901 --bind 127.0.0.1` from the repo root.
2. Open the hosted HTML on `127.0.0.1` in the tab, evaluate
   `linkedin-article.js` there, then `await lia.stash()`. It writes the adapted
   HTML and the counts to compare against into `window.name`. Read its `first`
   and `inkChars` against the file you just built (next section).
3. Navigate the same tab to `https://www.linkedin.com/article/new/`.
   `window.name` arrived intact (16,791 characters on the first run), unlike on
   `linkedin.com/feed`, where `references/linkedin.md` records it arriving empty.
4. Evaluate `linkedin-article.js` again, then `await lia.paste()`,
   `lia.setTitle(title)`, the cover (below), and `lia.audit()`.
5. Reload the tab, evaluate the file once more, and `lia.audit()` again. That
   second audit is the one that counts.

**The first input creates the draft.** `/article/new/` became
`/article/edit/<id>/` after the paste, with `Draft - saved` in the corner. Open
`/article/new/` once per article; to redo a body, `lia.clear(<id>)` and paste
again on the same URL.

## The tab's cache can hand over the previous build

MEASURED 2026-11-19. The article was edited and `make-medium.py` re-run, and the
`-hosted.html` on disk held the new text. The tab had opened the same
`127.0.0.1` URL earlier in the day, and both the navigation and `stash()`'s
`fetch(location.href)` were answered from the HTTP cache. The previous version
went into the editor, and `lia.audit()` read `problems: []`, because the stash
it compares against was the same stale copy: 7,527 non-space characters on both
sides, the figure from the run before the edit.

`stash()` now fetches with `cache: "no-store"` and returns `first` and
`inkChars`; the re-run read 7,853, and an audit of the stale draft against the
fresh stash reported `7527 non-space characters, sent 7853`. An audit that
agrees with the stash says the paste was faithful to the stash. That the stash
is the current build is a separate reading: compare `inkChars` with the number
from the earlier run, or look for a phrase the edit added.

## HTML cannot be parsed in the page

`new DOMParser().parseFromString(html, "text/html")` on the editor page returned
a body with **no element children**, for a source holding 269 tags: the title
and the stylesheet's text came back as one text run. `window.trustedTypes` has a
default policy on that page. Two pastes went in as plain text before this was
noticed, because the string handed to the paste had already lost its tags: one
paragraph, 42 link marks, `make-medium.py` linked to `http://make-medium.py`.

So every DOM operation on the article's HTML happens on `127.0.0.1`, in
`lia.stash()`, and `lia.stash()` refuses to run anywhere else. The paste itself
is unaffected: a `text/html` string given to a synthetic `ClipboardEvent("paste")`
is parsed by the editor into 3 code blocks, 7 headings, 10 list items and 39
paragraphs.

## Evaluate the helper's text; do not `eval` it from `window.name`

Carrying the helper's source in `window.name` and running `(0, eval)(js)` on the
editor page worked on most loads. On one load, the one where the `Next` modal had
been opened, the same line threw `EvalError: ... 'unsafe-eval' is not an allowed
source of script`, and it ran again on the two loads after. Which of the two
caused it is not isolated. Evaluate the file's text with the browser automation's
own JavaScript capability each time; `window.name` carries the HTML and the
counts only.

## Audit after a reload, not after the paste

The editor element carries its Tiptap instance (`.ProseMirror` → `.editor`), and
`editor.getJSON()` is the document. Right after a paste that document is what
the editor holds. **After a reload it is what LinkedIn stored**, and the two
differ:

| | After the paste | After a reload |
| --- | --- | --- |
| Inline code marks | 40 | **0** |
| Heading levels 1, 4, 5, 6 | kept | **paragraphs** |
| Image `src` | `raw.githubusercontent.com` | `media.licdn.com` |
| Text, links, code blocks, lists | as below | unchanged |

The save itself is a `POST` to
`/voyager/api/voyagerPublishingDashFirstPartyArticles/urn:li:fsd_firstPartyArticle:<id>`.
This kit does not call it: reading it back needs the session's CSRF token, and
the reload gives the same answer with no token.

`lia.audit()` compares the document with what `lia.stash()` sent and returns
`problems`: missing link targets, link targets the source does not hold, code
block line counts, image count and alt text, `h2`/`h3` counts, list items,
blockquotes, and the count of non-space characters. On the final run, after a
reload: `problems: []`, 4 of 4 link targets, code blocks of 2, 2 and 5 lines,
7 `h2`, 10 list items, 3 blockquotes, one re-hosted image with its alt text,
and 7,527 non-space characters on both sides.

## What the editor cannot hold

Read from the editor's schema (`.ProseMirror` → `.pmViewDesc.node.type.schema`),
then confirmed with a probe paste whose shape was read back:

| Sent | Arrived |
| --- | --- |
| `<table>`, 2x2 | one paragraph, `ABc1c2`. **There is no table node.** |
| a list inside a list item | the inner items run into the parent: `outer oneinner oneinner two` |
| a blockquote of two paragraphs | the first paragraph. **The second was dropped.** |
| `<ol start="3">` | an ordered list starting at 1 |
| `line one<br>line two` | `line one line two` |
| strike, underline, sub, sup | plain text |
| `<h4>`, and `<h2>` | a level 3 heading, both times |

`blockquote` and `listItem` each hold exactly one paragraph in the schema, which
is the cause of the second and third rows. `lia.stash()` splits a quote into one
blockquote per paragraph and moves nested items up behind their parent item;
the same probe through the helper arrived as four separate list items and two
quotes, with `problems: []`. A `<table>` in the source is reported by
`lia.audit()` and never repaired: `make-medium.py` has already drawn tables as
images.

## Headings: two levels are saved

The Style menu offers `Normal`, `Heading` and `Subheading`. Six probe headings,
levels 1 to 6, were inserted through the editor and all six rendered. After a
reload, level 2 was an `H2` at 24px/600, level 3 an `H3` at 20px/600, and levels
1, 4, 5 and 6 were paragraphs at the body's 16px.

The paste lands every heading at level 3 whatever tag it was sent as (`h4` on
one run, `h2` on the next). So `lia.stash()` records the level each heading
should have, the source's largest heading as 2 and every other as 3, and
`lia.paste()` sets them on the nodes afterwards. `make-medium.py` demotes
sections to `<h4>`; here they are `Heading`.

## Inline code: not saved, and worth keeping in the paste anyway

The schema has a `code` mark and the toolbar has a button for it, and a pasted
`<code>` shows as code. A reload returns the same text with no mark: 40 before,
0 after, on two separate pastes, while the 19 bold marks beside them survived
both times.

The mark still earns its place in the paste. With all 40 unwrapped beforehand,
the editor linked every bare name that looks like a host: `make-medium.py`
became a link to `http://make-medium.py`, `dev.to`, `SKILL.md` and
`window.name` likewise, 41 link marks for 4 real targets, and
`https://claude.com/claude-code` was rewritten to `http://`. With the marks left
on, nothing was linked, and the reload left plain text and 4 of 4 targets.

Two rules follow:

- **`<code>` inside a link is unwrapped.** The `code` mark has `excludes: "_"`,
  so a link around inline code keeps the code and loses the link: the first
  paste kept 2 of 4 targets, and the two missing were both `` [`path`](url) ``.
  `lia.stash()` unwraps those and only those.
- **A file name in running prose, outside backticks, becomes a link.**
  `make-medium.py` and `dev.to` in a plain sentence each gained an `http://`
  link in the probe. `lia.audit()` lists them under "links the source does not
  hold". Put the name in backticks in the source.

## Images are re-hosted from their URL

Each `<img>` on `raw.githubusercontent.com` became a `figureImage` holding an
`inlineImage` with a `urn:li:digitalmediaAsset:...` within a few seconds of the
paste, and after a reload its `src` was on `media.licdn.com`. The page called
`/voyager/api/voyagerVideoDashMediaUploadMetadata?action=upload` twice for the
two images of the first paste.
`lia.paste()` waits until every image has a `urn`.

**The paste leaves `alt` empty.** Both images arrived with `alt: ""` although
the source had alt text. Setting `alt` on the node through the editor held
through a reload, so `lia.paste()` writes the source's alt texts back in order.

Each figure has an optional caption field (`Add a caption (optional)`); it was
left empty. As on every destination that fetches by URL, the images must be
committed and pushed before the paste.

**An image alone in a `<p>` is dropped.** MEASURED 2026-11-19 on a second
article: `make-medium.py` writes an uncaptioned image as `<p><img></p>`, and all
9 such images pasted as nothing (0 `inlineImage`, no placeholder, no error).
Wrapped in `<figure>` the same 9 each became a `figureImage` with a `urn` and,
after a reload, a `media.licdn.com` source. `lia.stash()` now does that wrap and
reports `imagesFigured`. The first run's images were already in `<figure>`.

**A leading summary keeps the body cover.** `stash()` drops the leading image
only when nothing precedes it; with Medium's summary-then-cover order the cover
is the second block and stays, duplicating the cover slot. On that run it was
removed by hand on `127.0.0.1` before the navigation.

**Correction.** Neither wrapper is reliable, so `stash()` no longer wraps
anything. MEASURED 2026-11-19 on a third article: its two table images, sent as
`<figure><img></figure>` with the body, both pasted as nothing (0 of 2), where
the second article's nine had all arrived that way. Across three articles the
record is `<p><img></p>` 1 of 1 (twice) and 0 of 9, `<figure><img></figure>` 9 of
9 and 0 of 2; what decides it is not isolated. **One image pasted alone did
arrive**: `<p><img></p>` pasted with the caret at the end of the paragraph before
it became a `figureImage` with a `urn`, placed directly after that paragraph.
So `stash()` now replaces every body image with a marker paragraph
(`[[lia-image-0]]`), and `paste()` pastes each image alone at the end of its
marker, waits for its `urn`, and deletes the marker. On that article both went in
(`imagesIn: [{i: 0, ok: true}, {i: 1, ok: true}]`) and the reload read 2 re-hosted
images with their alt text and `problems: []`. A marker left in the body means
its image did not arrive; `audit()` reports it.

**Correction.** `stash()` now drops the first image when it sits above the
first heading, which covers both of `make-medium.py`'s positions for the cover.
MEASURED 2026-11-19 on a third article whose cover follows a summary paragraph:
`coverDropped` named the cover and the body kept its two table images.
`keepCover: true` still keeps it.

## The cover is its own slot, and it crops to 16:9

Above the title is `Add a cover image or video to your article`, so the cover
does not belong in the body. `lia.stash()` drops the leading image that
`make-medium.py` puts there for Medium (`keepCover: true` keeps it).

- `Upload from computer` opens an `Add cover image or video` dialog and calls
  `input.click()` on `#media-editor-file-selector__file-input`, a light-DOM input
  accepting JPEG, PNG, WebP and video. Patch `HTMLInputElement.prototype.click`
  for that one call so no native picker opens, label the input, `find` it and
  `file_upload` into it.
- **A 1376x578 cover previewed as 1027x578**: the slot crops to 16:9 from the
  centre. The 1200x675 Builder Center cover previewed whole at 1200x675. Upload
  the 16:9 cover (`make-cover.py --mode builder`).
- `Next` in the dialog closes it; the editor then shows buttons labelled
  `Click to edit the cover image of article` and `Click to remove the cover image
  of article`, and a field `Add credit and caption`. The cover was still there
  after later reloads and `lia.clear()` calls: clearing the body leaves it.

`lia.coverInput()` and `lia.coverNext()` carry this route. The upload above was
driven step by step before those two functions were written; of the two, only
`coverInput()`'s refusal on an article that already has a cover has run.

**Correction.** Both have run since. MEASURED 2026-11-19 on a later article:
`coverInput()` clicked the button and returned `the dialog opened without a file
input`, because it read the dialog in the same tick; the input was there a moment
later and took the file. It now waits up to five seconds. `coverNext()` returned
`{cover: true, preview: "1200x675"}`.

## Title

The title is `#article-editor-headline__textarea`, placeholder `Title`,
`maxLength` 150. `lia.setTitle()` sets it through the native value setter with
`input` and `change`, and refuses a title over 150 characters. The title came
back after every reload. There is no subtitle field.

## Preview, and where publishing starts

`Manage` lists Preview, Duplicate as draft, Settings, Drafts, Scheduled,
Published, New draft and Create newsletter.

- **A scripted `.click()` on `Preview` did nothing.** A coordinate click on the
  same item moved the tab to `/pulse/draft/preview/<id>/`.
- The preview rendered 3 `<pre>` of 2, 2 and 5 lines, 3 blockquotes, 10 list
  items, the 4 link targets, and the cover at 1200x675 (shown 720x405).
- **The preview page has its own `Publish` button**, beside `Back to edit` and
  `Share draft`. Reading the preview is safe; there is nothing to click on it.
- **`Next` in the editor opens a `Create post modal`**: a text box reading
  `Tell your network what your article is about…`, the audience (`Post to
  Anyone`), `Schedule post`, and **`Publish`**. Focus lands in the text box.
- `Dismiss` on that modal asks `Discard draft: You haven't finished your post
  yet. Are you sure you want to leave and discard your draft?`. **`Discard`
  discards the post text only.** The article was intact afterwards: 9,083
  characters, the title, `Draft - saved`.

Not measured, because nothing was published: what `Publish` does, whether the
post text is required, the published URL's shape, and how an edit to a published
article is saved. Publishing is the author's click, and there is no `links.txt`
key for the article yet.

**Correction.** The first three of those four are measured in the next section,
and the key now exists. How an edit to a published article is saved is still
unmeasured.

## Publishing

MEASURED 2026-11-19, publishing this kit's article at the author's request, in a
visible tab.

- **`Next` took a ref click** from `find` this time; the earlier run used a
  coordinate click. A scripted `.click()` on `Next` is untested.
  **Correction.** MEASURED 2026-11-19 on the next article: `find` returned no ref
  for `Next`, and a scripted `.click()` on the button opened the modal.
- **`Publish` is enabled with the post box empty.** The modal read `Post to
  Anyone`, the box held no text, and one scripted click on `Publish` published
  the article. The post text is optional.
- **The tab moves to `/pulse/<slug>/?published=t`** within four seconds, under a
  dialog headed `Congrats on publishing your latest article`, with share buttons
  and `Get the link to this article`. Dismiss it.
- **The slug is LinkedIn's.** "Streamline Publishing with a Claude Code Skill"
  published as `/pulse/streamline-publishing-claude-code-skill-william-mclean-kay8c/`:
  "with" and "a" are gone, and the author's name and five characters are added.
  Take the URL from the page, never from the title.
- **Publishing also creates a feed post.** The published page links `Edit
  article` (`/article/edit/<id>/`, the draft's id) and `View post`
  (`/feed/update/urn:li:ugcPost:<id>/`).
- **The published page matches the draft**: 3 `<pre>` of 2, 2 and 5 lines,
  3 blockquotes, 10 list items, the 4 link targets, and the cover at 1200x675.

`lia.publishSettings()`, `lia.publish({audience, postText})` and
`lia.published()` carry this route. `publish()` refuses unless the audience and
the post text it finds are the ones it was given, and clicks after returning,
since the navigation ends a script still running in the page. The publish above
was driven step by step with that same click before the three functions were
written; their refusals are covered in `tests/`.

**Correction.** All three have run on a real publish since. MEASURED 2026-11-19:
`publishSettings()` read `{audience: "Anyone", postText: "", button: "Publish"}`,
`publish({audience: "Anyone", postText: ""})` returned `{clicked: "Publish"}`, and
on the published page `published()` returned the URL
(`/pulse/publishing-markdown-linkedin-article-from-agent-skill-william-mclean-kg40c/`:
"to" and "a" dropped from the title), the edit id and the feed post's URL.

**The save badge is read from outside the editor.** The helper matched `Draft -
saved` over the whole page, and on an article that quotes that phrase it returned
a line of the article's own text. It now reads the badge element.

## Links: a 200 from `/pulse/` proves nothing

MEASURED 2026-11-19 with `check-links.py`'s fetch (browser User-Agent, no
cookies). The published article answered 200 at its own URL, and the served page
held the title and a sentence added in that day's edit. **A slug that does not
exist also answered 200**: `linkedin.com/pulse/this-slug-does-not-exist-zz9zz9/`
redirected to `/top-content/?trk=article_not_found`, titled "Top Content on
LinkedIn". `check-links.py` now fails a URL that lands on
`trk=article_not_found`. The feed post's URL answered 200 as well.

Record the article in `links.txt` as `linkedin-article = <url>`; a draft has no
public URL, so `PENDING` until then. `check-links.py` fetches it.
`make-linkedin.py` accepts the key and leaves it out of the post, which is on the
same site. The Slack and Google Chat posts do not carry it.

## Not measured

- Editing a published article: whether `/article/edit/<id>/` saves to the live
  page or to a draft copy, and what the button reads.
- What a post text typed into the `Create post modal` looks like on the feed
  post, and scheduling.
- A hidden tab. Every step above ran with `document.visibilityState === "visible"`.
- Image size limits, and what the editor does with an image URL it cannot fetch.
- Whether a newsletter issue (`Create newsletter`) uses the same editor.
- Whether any LinkedIn API can create or draft a native article. Not looked up
  here; `references/linkedin.md` covers the Posts API, which cannot draft a post.

## The first image can miss while the draft is being created

MEASURED 2026-11-20 on the zombie-sweep-gcp article, visible tab, five table images. `paste()`'s image loop ran while `/article/new/` was still becoming `/article/edit/<id>/`: image 0 returned `no image appeared; its marker is left in place` and images 1 to 4 arrived. Pasting image 0 alone at its marker again, after the URL had changed, gave it a `urn` within the 30 s wait. Because `paste()` writes alts in document order, the missing image had shifted every alt by one; re-running the alt pass after the retry put all five back in source order, and the reload audit read `problems: []`. Retry a missed image at its marker, then rewrite the alts, before reloading.

On the same run, `(0, eval)(js)` from `window.name` threw `EvalError` (no `unsafe-eval`) on the first load of `/article/new/`, as recorded above; the needed functions were inlined into the evaluated script instead.
