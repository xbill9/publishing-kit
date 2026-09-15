#!/usr/bin/env bash
# PreToolUse / Write|Edit.
#
# Content-addressed covers (cover.77acc7c4.jpg) and the Medium image set are
# generated output: the filename is a digest of the bytes, so editing one in
# place leaves a name that no longer describes its contents. Regenerating is
# idempotent -- identical bytes reproduce the identical name.
set -uo pipefail

f=$(jq -r '.tool_input.file_path // empty')
[ -n "$f" ] || exit 0
b=${f##*/}

deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}\n' \
    "$(jq -Rn --arg m "$1" '$m')"
  exit 0
}

if printf '%s' "$b" | grep -qE '^cover.*\.[0-9a-f]{6,}\.(jpg|jpeg|png|webp)$'; then
  deny "$b is a content-addressed cover: its name is a digest of its bytes, so it must be regenerated with scripts/make-cover.py, not edited in place."
fi

case "$f" in
  */medium/img/*)
    deny "$b is generated Medium output: regenerate the whole set with scripts/make-medium.py rather than editing one image in place."
    ;;
esac

exit 0
