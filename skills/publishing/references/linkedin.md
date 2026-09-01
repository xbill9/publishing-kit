# LinkedIn, from the API documentation

LinkedIn is the fourth destination and the only one that renders **no markup at
all**. Everything here is from LinkedIn's own developer documentation rather than
from a run, because the platform behaviours below are stated first-party and the
account-facing ones cannot be measured without publishing.

Sources, all first-party:

- Posts API — https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
- little Text Format — https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/little-text-format
- Share on LinkedIn — https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin

## There are two APIs, and both publish immediately

| | Posts API | UGC Posts API |
| --- | --- | --- |
| Endpoint | `POST /rest/posts` | `POST /v2/ugcPosts` |
| Text field | `commentary`, `little` format | `specificContent…shareCommentary.text` |
| Versioned | yes, `LinkedIn-Version: YYYYMM` | no |
| Access | Marketing / Community Management | **self-serve** |

Self-serve access is the "Share on LinkedIn" product, added from the Developer
Portal under My Apps → Products. It grants `w_member_social`, "required to create
a LinkedIn post on behalf of the authenticated member." Auth is three-legged
OAuth 2.0 — an access token per member, not a static key in a file like
`~/.devto.key`.

Rate limits, first-party: **150 requests per member per day**, 100,000 per
application per day.

A URL share sets `shareMediaCategory: ARTICLE` with `originalUrl`, `title` and
`description`, so the preview card is stated rather than scraped. The newer Posts
API is explicit that it "does not support URL scraping for article post creation."

## The API cannot create a draft

`lifecycleState` documents `DRAFT` as "content that's accessible only to the
author and is not yet published", and then states that `PUBLISHED` **"is the only
accepted field during creation."** DRAFT is a state you can read back, never one
you can post into. The self-serve API says the same thing in fewer words: "For the
purposes of creating a share, the lifecycleState will always be `PUBLISHED`."

Both APIs do support delete — `DELETE /rest/posts/{urn}`, idempotent, 204 — which
dev.to does not.

There is therefore no LinkedIn equivalent of dev.to's `published: false`. Anything
that posts through the API is publishing, not drafting. **The draft is a text
file, and the composer is where it becomes a draft.** `make-linkedin.py` writes
that file and never posts.

## Managing a post after it exists: three of four verbs

Once a post exists you can edit and delete it through the API. You cannot reliably
read it back.

| Verb | Endpoint | Permission | Self-serve? |
| --- | --- | --- | --- |
| Create | `POST /rest/posts` | `w_member_social` | **yes**, Share on LinkedIn |
| Update | `POST /rest/posts/{urn}` with `X-RestLi-Method: PARTIAL_UPDATE` | `w_member_social` | **yes** |
| Delete | `DELETE /rest/posts/{urn}` — idempotent, 204 | `w_member_social` | **yes** |
| Read / list | `GET /rest/posts/{urn}`, `?q=author` | `r_member_social` | **no** |

`r_member_social` is documented as **"restricted and is available to approved
users only."** So an account with the self-serve product can post, edit and delete
its own content, and cannot list it.

Only these fields are patchable: `commentary`, `contentCallToActionLabel`,
`contentLandingPage`, `lifecycleState`, `adContext`. Editing the post text is
therefore supported; changing an attached article's URL after the fact is not.

**The consequence for any tooling: keep the URN yourself.** Creation returns it in
the `x-restli-id` response header, and without `r_member_social` that header is the
only chance to learn it. This is the opposite of dev.to, where `/api/articles/me`
hands back the whole catalogue whenever you ask — which is exactly why the dev.to
guidance in `SKILL.md` says to read state from the listing.

## The post field takes three kinds of thing, and no formatting

Post text is `commentary`, in LinkedIn's `little` format. Its entire element set:

| Element | Example |
| --- | --- |
| TextElement | `Hello World` |
| MentionElement | `@[Devtestco](urn:li:organization:2414183)` |
| HashtagElement / HashtagTemplate | `#hashtag`, `{hashtag\|#\|mytag}` |

**No bold, no italics, no lists, no link markup.** A markdown `**bold**` or
`[label](url)` arrives as its own punctuation. Bullets are literal characters, and
the documentation's own example writes them as escaped asterisks.

## Every reserved character must be escaped, used as markup or not

Quoting the spec: *"All reserved characters need to be escaped with a backslash,
even if those characters are not used in one of the supported elements or
templates."*

```
|  {  }  @  [  ]  (  )  <  >  #  \  *  _  ~
```

An article body is full of them — `body_markdown`, `organization_id`, any
parenthesis, any `@` in a Medium URL. `make-linkedin.py --api` emits the escaped
variant. **This applies to the API only.** Text typed or pasted into the composer
needs no escaping, which is why the default output is unescaped.

## Mentions match by name, case sensitively

The text linking to a mentioned entity must match the entity's name for the link
to convert, and matching is case sensitive. Organization mentions must match the
**full** name; a person mention may match any one name in the full name. No match
means it silently renders as ordinary text.

## Numbers that are NOT first-party

LinkedIn's documentation gives no character limit for `commentary`. It gives only
the error `FIELD_LENGTH_TOO_LONG`. Two figures in `make-linkedin.py` come from
third-party counters and consensus, not from LinkedIn:

| Figure | Value | Status |
| --- | --- | --- |
| Post limit | 3,000 characters | third-party consensus, treated as a hard stop |
| "…see more" fold | ~140 mobile, ~210 desktop | third-party, moves with screen and font size |

They are enforced anyway, because overshooting either is a worse outcome than a
conservative cut. **If they are ever measured directly, record the measurement
here and mark it MEASURED with a date.**

## No Unicode pseudo-bold

Having no bold, the common workaround is the Mathematical Alphanumeric Symbols
block — 𝗕𝗢𝗟𝗗 built from U+1D400–U+1D7FF. A screen reader announces those code
points individually or skips them, so the headline becomes the least readable part
of the post. `make-linkedin.py` fails the run if any appear.

## What the generator checks

Five, and it exits non-zero on any of them:

1. Every link resolves. A `PENDING` value is carried into the file as a visible
   placeholder **and** fails, so a post with an unpublished link cannot go out.
2. The hook fits the fold.
3. The post fits the limit.
4. No markdown survives — `**`, `](`, backticks, `##`.
5. No Unicode pseudo-bold.

Two dev.to articles routed to two organizations are two different URLs. Label them
distinctly, or the post shows the same word against two links.

## Driving the composer: everything else in this kit fails here

MEASURED 2026-09-01 filling a real post. LinkedIn breaks all three techniques
that work on Medium and AWS Builder Center, and none of them fail loudly.

**`window.name` does not survive.** Loading a payload same-origin from localhost
and navigating to `linkedin.com` arrives with `window.name` empty. That is the
trick that carries 34 KB into Medium in one step, and it is unavailable here. A
post is capped at 3,000 characters, so embedding the text directly in the
injected script is always sufficient instead.

**The editor is inside a SHADOW ROOT.** `document.querySelector('[contenteditable]')`
returns nothing while the composer is plainly open on screen — a blank result
that looks exactly like "not loaded yet". Walk the shadow roots:

```js
function findEditor(root) {
  for (const el of root.querySelectorAll('*')) {
    if (el.shadowRoot) {
      const hit = [...el.shadowRoot.querySelectorAll('[contenteditable="true"],[role="textbox"]')]
        .find(e => e.offsetParent !== null || e.getClientRects().length);
      if (hit) return hit;
      const deeper = findEditor(el.shadowRoot);
      if (deeper) return deeper;
    }
  }
  return null;
}
```

It is a Quill editor: `class="ql-editor ql-blank"`, `aria-placeholder="What do
you want to talk about?"`.

**A synthetic paste event does nothing.** Dispatching `ClipboardEvent("paste")`
with a `DataTransfer` — the method that works on both other editors — left the
composer at **1 character**, with no error. What works is selecting the contents
and calling `document.execCommand("insertText", false, POST)`. Verify with a
one-line probe before committing the full payload.

**Stop at the composer.** The Post button goes to a network and there is no draft
state the API can reach afterwards. Read the post back and let a person press it.
