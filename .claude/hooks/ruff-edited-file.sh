#!/usr/bin/env bash
# PostToolUse / Write|Edit.
#
# There is no CI here, so without this a lint mistake surfaces only when
# preflight.py fails an article. Runs ruff on just the file that was edited and
# feeds anything left over back as context, so a defect is visible immediately
# rather than three commits later.
set -uo pipefail

f=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty')
[ -n "$f" ] || exit 0
case "$f" in *.py) ;; *) exit 0 ;; esac
[ -f "$f" ] || exit 0
command -v ruff >/dev/null 2>&1 || exit 0

# --fix only applies ruff's safe fixes; unsafe ones are left for a human.
ruff check --quiet --fix "$f" >/dev/null 2>&1

# Silent on success: only a non-zero ruff exit is worth the model's attention.
out=$(ruff check --no-cache --output-format=concise "$f" 2>&1)
rc=$?
[ "$rc" -eq 0 ] && exit 0
[ -n "$out" ] || exit 0

jq -Rn --arg o "$out" \
  '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: ("ruff on the file just edited:\n" + $o)}}'
