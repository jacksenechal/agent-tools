#!/usr/bin/env bash
# Tests check_no_hardcoded_paths.sh against generated fixtures: each "bad" line must be
# flagged and each "good" line must pass. Fixtures are written to a temp dir at run time,
# since a committed bad fixture would fail the whole-repo check.
set -euo pipefail

guard="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check_no_hardcoded_paths.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# Assembled from pieces so this file does not trip the guard itself.
h=/home; u=/Users; w=workspace
bad=(
  "cd ~/$w/project"
  "cat \$HOME/$w/notes.md"
  "ls \${HOME}/$w"
  "ExecStart=%h/$w/bin/run"
  "open $h/someone/repo/file"
  "open $u/someone/repo/file"
)
good=(
  "cd \"\$REPO_PATH\""
  "mount $h/pwuser/state"
  "cp file $h/node/app/"
  "data in $h/arcadedb/databases/"
  "workspace is a word, ~/projects is fine"
  "\${XDG_DATA_HOME:-\$HOME/.local/share}/tool"
)

fail=0
for i in "${!bad[@]}"; do
  f="$tmp/bad$i.md"; printf '%s\n' "${bad[$i]}" > "$f"
  if "$guard" "$f" >/dev/null 2>&1; then echo "FAIL not flagged: ${bad[$i]}"; fail=1; else echo "ok   flagged: ${bad[$i]}"; fi
done
for i in "${!good[@]}"; do
  f="$tmp/good$i.md"; printf '%s\n' "${good[$i]}" > "$f"
  if "$guard" "$f" >/dev/null 2>&1; then echo "ok   passed: ${good[$i]}"; else echo "FAIL flagged: ${good[$i]}"; fail=1; fi
done
exit $fail
