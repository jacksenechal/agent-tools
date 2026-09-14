#!/usr/bin/env bash
#
# sync_archetypes.sh — keep the resume repo's role/* archetypes current with main.
#
# For each role/* branch: merge main in. A merge that touches only the SOURCE
# cleanly (resume.md and friends) is auto-completed, republished, committed, and
# pushed. Generated artifacts (index.html, resume.pdf) diverge on every branch
# and would always conflict, so those conflicts are noise: they are resolved by
# regenerating from the merged source, not counted as a real conflict. A real
# conflict in resume.md (or any non-generated file) is left un-merged, aborted,
# and reported — that archetype has drifted far enough from main that it needs a
# content REFRESH (re-derive from current main + its role positioning), which is
# a judgment task, not a merge. Lazy path: it also gets refreshed the next time
# that role is tailored (see the job-search skill, Stage 2).
#
# Usage: sync_archetypes.sh [--no-push] [--dry-run]
#
# Env: RESUME_REPO_PATH (default ~/workspace/resume)

set -uo pipefail

REPO="${RESUME_REPO_PATH:-$HOME/workspace/resume}"
GENERATED_RE='^(index\.html|resume\.pdf)$'
PUSH=1
DRY=0
for arg in "$@"; do
  case "$arg" in
    --no-push) PUSH=0 ;;
    --dry-run) DRY=1; PUSH=0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

cd "$REPO" || { echo "resume repo not found at $REPO" >&2; exit 1; }

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: resume working tree is not clean; commit/stash first." >&2
  git status --short >&2
  exit 1
fi

START_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
restore() { git checkout --quiet "$START_BRANCH" 2>/dev/null || true; }
trap restore EXIT

git fetch --quiet origin 2>/dev/null || echo "warn: git fetch failed (offline?); syncing against local main" >&2

git checkout --quiet main || { echo "ERROR: cannot checkout main" >&2; exit 1; }
git pull --quiet --ff-only origin main 2>/dev/null || echo "warn: could not fast-forward main from origin" >&2

CLEAN=(); CONFLICT=(); UPTODATE=(); FAILED=()

for ref in $(git for-each-ref --format='%(refname:short)' refs/heads/role/); do
  behind="$(git rev-list --count "${ref}..main")"
  if [[ "$behind" -eq 0 ]]; then
    UPTODATE+=("$ref"); continue
  fi

  if [[ "$DRY" -eq 1 ]]; then
    # Predict outcome without mutating anything (git >= 2.38 merge-tree).
    if out="$(git merge-tree --write-tree main "$ref" 2>/dev/null)"; then
      CLEAN+=("$ref ($behind behind)")
    else
      # Conflicted paths are the tab-terminated stage entries in the output.
      conflicts="$(printf '%s\n' "$out" | awk -F'\t' 'NF==2 {print $2}' | sort -u | grep -vE "$GENERATED_RE" || true)"
      if [[ -z "$conflicts" ]]; then
        CLEAN+=("$ref ($behind behind)")
      else
        CONFLICT+=("$ref ($behind behind): $(echo $conflicts)")
      fi
    fi
    continue
  fi

  git checkout --quiet "$ref" || { FAILED+=("$ref (checkout)"); continue; }

  if git merge --no-edit --no-ff main >/dev/null 2>&1; then
    : # merged clean outright
  else
    unmerged="$(git diff --name-only --diff-filter=U)"
    real="$(echo "$unmerged" | grep -vE "$GENERATED_RE" || true)"
    if [[ -n "$real" ]]; then
      git merge --abort
      CONFLICT+=("$ref ($behind behind): $(echo "$real" | tr '\n' ' ')")
      continue
    fi
    # Only generated artifacts conflicted: source merged fine, so complete the
    # merge and let _publish regenerate them from the merged resume.md.
    git checkout --ours -- $(echo "$unmerged" | tr '\n' ' ') 2>/dev/null || true
    git add $(echo "$unmerged" | tr '\n' ' ') 2>/dev/null || true
  fi

  if ! ./_publish >/dev/null 2>&1; then
    echo "warn: _publish failed on $ref (artifacts may be stale)" >&2
  fi
  git add -A
  if [[ -n "$(git status --porcelain)" || -n "$(git log --oneline main.."$ref" 2>/dev/null)" ]]; then
    git commit --quiet --no-edit 2>/dev/null || \
      git commit --quiet -m "sync ${ref} with main (${behind} commit(s) behind)" 2>/dev/null || true
  fi
  if [[ "$PUSH" -eq 1 ]]; then
    git push --quiet origin "$ref" 2>/dev/null || echo "warn: push failed for $ref" >&2
  fi
  CLEAN+=("$ref ($behind behind)")
done

restore
trap - EXIT

echo
echo "=== Archetype sync report ==="
printf '%s\n' "Up to date (${#UPTODATE[@]}):"; for r in "${UPTODATE[@]:-}"; do [[ -n "$r" ]] && echo "  = $r"; done
printf '%s\n' "Synced clean (${#CLEAN[@]}):";   for r in "${CLEAN[@]:-}";   do [[ -n "$r" ]] && echo "  + $r"; done
printf '%s\n' "Need refresh — conflicted (${#CONFLICT[@]}):"; for r in "${CONFLICT[@]:-}"; do [[ -n "$r" ]] && echo "  ! $r"; done
[[ "${#FAILED[@]}" -gt 0 ]] && { echo "Failed (${#FAILED[@]}):"; for r in "${FAILED[@]:-}"; do [[ -n "$r" ]] && echo "  x $r"; done; }
echo
if [[ "${#CONFLICT[@]}" -gt 0 ]]; then
  echo "Conflicted archetypes have drifted too far for a merge and need a content"
  echo "refresh (re-derive resume.md from current main + the role's positioning)."
  echo "They are also refreshed automatically the next time that role is tailored."
fi
[[ "$DRY" -eq 1 ]] && echo "(dry run: nothing was changed, committed, or pushed)"
exit 0
