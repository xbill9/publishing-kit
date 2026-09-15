#!/usr/bin/env bash
# PostToolUse / Write|Edit.
#
# .claude-plugin/plugin.json is canonical and the only file holding "version".
# The repo-root plugin.json is the Codex/agy host surface and must be a copy of
# it. Version bumps historically touched only the canonical file, so the root
# copy drifted silently. This regenerates it instead of relying on memory.
#
# The repo root is derived from the edited path, not from the cwd, so this works
# wherever the hook is invoked from.
set -uo pipefail

f=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty')
[ -n "$f" ] || exit 0

case "$f" in
  */.claude-plugin/plugin.json)
    root=${f%/.claude-plugin/plugin.json}
    ;;
  *) exit 0 ;;
esac

[ -f "$f" ] || exit 0
cmp -s "$f" "$root/plugin.json" && exit 0

cp "$f" "$root/plugin.json" || exit 0
printf '{"systemMessage":"Regenerated root plugin.json from .claude-plugin/plugin.json"}\n'
