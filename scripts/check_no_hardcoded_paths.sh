#!/usr/bin/env bash
# Fails if any skill, script, asset or doc in this repo hard-codes a machine-specific path:
# a fixed workspace layout (~/workspace/..., $HOME/workspace/..., %h/workspace/...) or a
# specific user's home directory (/home/<user>/..., /Users/<user>/...).
#
#   scripts/check_no_hardcoded_paths.sh            check the whole repo
#   scripts/check_no_hardcoded_paths.sh <file>...  check specific files (the pre-commit hook does this)
#
# Container-internal homes (/home/pwuser, /home/node, /home/arcadedb) are allowed. archive/ is not checked.
# Fix a finding by resolving the path at run time (env var, config file, the script's own
# location), never by adding it to an allowlist here. See AGENTS.md, "No hard-coded paths".

set -uo pipefail
cd "$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)" || exit 2

PATTERN='(~|\$HOME|\$\{HOME\}|%h)/workspace\b|/home/(?!pwuser/|node/|arcadedb/)[a-z_][a-z0-9_.-]*/|/Users/[A-Za-z0-9_.-]+/'

if (( $# )); then
  files=("$@")
else
  mapfile -t files < <(git ls-files)
fi

status=0
for f in "${files[@]}"; do
  case "$f" in
    archive/*|scripts/check_no_hardcoded_paths.sh|*/mcp-playwright-novnc|*/mcp-playwright-novnc/*) continue ;;
  esac
  [[ -f "$f" ]] || continue
  if grep -nP -I "$PATTERN" "$f" /dev/null; then status=1; fi
done

if (( status )); then
  echo >&2
  echo "Hard-coded paths found (above). Resolve them at run time instead; see AGENTS.md." >&2
fi
exit $status
