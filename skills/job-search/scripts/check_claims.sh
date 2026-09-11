#!/usr/bin/env bash
# Deterministic last-mile check on externally-facing job-search writing.
#
#   check_claims.sh <file> [<file>...]   check specific files
#   check_claims.sh --all                sweep every external artifact in both repos
#
# Catches the mechanical error classes only: banned claim strings (from
# strategy/claim-guards.txt) and em/en dashes. Judgment calls are the fact-check
# agent's job; see references/external-output-gate.md.
#
# Exit 0 = clean, 1 = findings, 2 = misconfigured.

set -uo pipefail

JOBS_DIR="${JOBS_DIR:-$HOME/workspace/jobs}"
RESUME_DIR="${RESUME_DIR:-$HOME/workspace/resume}"
GUARDS="${CLAIM_GUARDS:-$JOBS_DIR/strategy/claim-guards.txt}"

[[ -f "$GUARDS" ]] || { echo "check_claims: no guards file at $GUARDS" >&2; exit 2; }

collect_all() {
  # External artifacts only. Research and strategy docs are internal and not swept
  # for dashes, but banned claims still matter there, so they are included.
  find "$JOBS_DIR/applications" "$JOBS_DIR/outreach" "$JOBS_DIR/strategy" \
       -name '*.md' -not -path '*/archived/*' 2>/dev/null
  [[ -f "$RESUME_DIR/resume.md" ]] && echo "$RESUME_DIR/resume.md"
}

# Captured or audit content: scraped postings/research about a company, and per-application
# fact-check logs that quote the wrong claims they caught. Not Jack's outgoing claims, so guards
# about Jack do not apply. Skipped entirely.
is_source_capture() {
  case "$1" in
    *job-posting.md|*glassdoor.md|*-research.md|*application-form.md|*fact-check.md) return 0 ;;
    *) return 1 ;;
  esac
}

# Source-of-truth docs state the banned strings on purpose, in order to ban them.
is_guard_doc() {
  case "$1" in
    */strategy/facts.md|*/strategy/narrative.md|*/strategy/claim-guards.txt) return 0 ;;
    *) return 1 ;;
  esac
}

is_external() {
  case "$1" in
    */README.md) return 1 ;;
    *cover-letter*|*application-responses*|*message*|*resume.md) return 0 ;;
    *) return 1 ;;
  esac
}

findings=0
report() { printf '%s\n' "$1"; }
finding() { findings=$((findings + 1)); }

if [[ "${1:-}" == "--all" ]]; then
  mapfile -t FILES < <(collect_all)
else
  [[ $# -gt 0 ]] || { echo "usage: check_claims.sh <file>... | --all" >&2; exit 2; }
  FILES=("$@")
fi

for f in "${FILES[@]}"; do
  [[ -f "$f" ]] || { finding; report "MISSING  $f"; continue; }
  is_source_capture "$f" && continue

  # Banned claim strings. Split on the first and last '|' only, so a guard regex
  # may itself contain '|' alternation.
  is_guard_doc "$f" || while read -r line; do
    kind="${line%%|*}"
    # BAN  = banned anywhere in the corpus.
    # BANX = banned only in externally-facing text (research notes may quote it).
    case "$kind" in
      BAN) ;;
      BANX) is_external "$f" || continue ;;
      *) continue ;;
    esac
    rest="${line#*|}"
    pattern="${rest%|*}"
    message="${rest##*|}"
    while IFS=: read -r lineno text; do
      [[ -n "$lineno" ]] || continue
      finding; report "BANNED   $f:$lineno"
      report "         match: $(echo "$text" | sed 's/^[[:space:]]*//' | cut -c1-100)"
      report "         fix:   $message"
    done < <(grep -nEi -- "$pattern" "$f" 2>/dev/null)
  done < <(grep -v '^[[:space:]]*#' "$GUARDS" | grep -v '^[[:space:]]*$')

  # Dashes: the draft itself only, not notes about a draft. Jack's hard rule.
  # Headings, list/field labels, attributions, and numeric ranges are exempt.
  if is_external "$f"; then
    while IFS=: read -r lineno text; do
      [[ -n "$lineno" ]] || continue
      finding; report "DASH     $f:$lineno"
      report "         $(echo "$text" | sed 's/^[[:space:]]*//' | cut -c1-100)"
      report "         fix:   no em/en dashes in outward-facing text. Use a comma, period, or colon."
    done < <(grep -nP '[\x{2013}\x{2014}]' "$f" 2>/dev/null \
             | grep -vP ':\s*#' \
             | grep -vP ':\s*[*_>-]*\s*[\x{2013}\x{2014}]\s' \
             | grep -vP ':\s*[-*]?\s*\*\*[^*]+\*\*\s*[\x{2013}\x{2014}]' \
             | grep -vP '\d[\d,.]*\s*[\x{2013}\x{2014}]\s*\$?\d')
  fi
done

echo
if [[ $findings -eq 0 ]]; then
  echo "CLEAR (${#FILES[@]} file(s) checked)"
  exit 0
fi
echo "$findings finding(s) across ${#FILES[@]} file(s)"
exit 1
