#!/bin/bash
#
# make_resume_workday.sh — render a résumé markdown file to a plain, single-column .docx
# aimed at Workday's "Autofill with Resume" parser, which mangles the styled house-style PDF
# (make_resume_pdf.sh). Same source markdown, different render target.
#
# Usage:
#   make_resume_workday.sh <input.md> [output.docx] [--name "..."] [--keep-md]
#
# This script is general-purpose and contains NO personal details. The applicant name must
# be supplied by the caller, either via --name or the $JOB_SEARCH_APPLICANT_NAME env var
# (source it from your private profile, e.g. ~/workspace/jobs/profile.md). The script errors
# if no name is given.
#
# Defaults:
#   output.docx -> same dir as input, named "Resume - <Name> - <Role>.docx", where <Role> is
#                  read off a sibling "Resume - <Name> - <Role>.pdf" in the input's directory
#                  (the file make_resume_pdf.sh already produced there). If no such PDF
#                  exists, <Role> cannot be derived and an explicit output path is required.
#   --name       -> $JOB_SEARCH_APPLICANT_NAME (required if the flag is omitted)
#   --keep-md    -> also write the intermediate cleaned markdown as "<output base>.workday.md"
#                   beside the docx (off by default).
#
# Transform: resume_to_workday_md.py (beside this script) rewrites the house-style résumé
# markdown into plain, single-column markdown — contact block as one item per line, section
# headers renamed to standard words and promoted to real headings, each job entry split into
# separate Job Title / Company / Location / Date lines with full month names, "Scope:"
# sub-lines de-italicized into a plain line, all bold/italic/link formatting stripped to plain
# text, em/en dashes to hyphens. See that script's module docstring for the full rule set and
# the Kantata multi-role caveat. Any source line it couldn't fully normalize (e.g. a year-only
# date range with no month to expand) is reported to stderr as a NOTE — read those before
# trusting the output blindly.
#
# pandoc then renders that markdown straight to .docx. Markdown headers become real Word
# Heading styles; nothing here introduces tables, columns, or text boxes.
#
# Requires: pandoc, python3.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_HELPER="$SCRIPT_DIR/resume_to_workday_md.py"

NAME="${JOB_SEARCH_APPLICANT_NAME:-}"
INPUT=""
OUTPUT=""
KEEP_MD=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)     NAME="$2"; shift 2 ;;
    --keep-md)  KEEP_MD=1; shift ;;
    -h|--help)  grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)
      if [[ -z "$INPUT" ]]; then INPUT="$1"
      elif [[ -z "$OUTPUT" ]]; then OUTPUT="$1"
      else echo "Unexpected arg: $1" >&2; exit 1
      fi
      shift ;;
  esac
done

if [[ -z "$INPUT" || ! -f "$INPUT" ]]; then
  echo "Error: input markdown file not found. Usage: $0 <input.md> [output.docx] [--name ..] [--keep-md]" >&2
  exit 1
fi

if [[ -z "$NAME" ]]; then
  echo "Error: applicant name required. Pass --name \"...\" or set \$JOB_SEARCH_APPLICANT_NAME" >&2
  echo "       (source it from your private profile, e.g. ~/workspace/jobs/profile.md)." >&2
  exit 1
fi

if [[ -z "$OUTPUT" ]]; then
  IN_DIR="$(cd "$(dirname "$INPUT")" && pwd)"
  # Look for the sibling PDF make_resume_pdf.sh already produced, and reuse its <Role>.
  MATCH=""
  for f in "$IN_DIR/Resume - $NAME - "*.pdf; do
    [[ -e "$f" ]] && MATCH="$f" && break
  done
  if [[ -n "$MATCH" ]]; then
    BASE="$(basename "$MATCH")"
    ROLE="${BASE#Resume - "$NAME" - }"
    ROLE="${ROLE%.pdf}"
    OUTPUT="$IN_DIR/Resume - $NAME - $ROLE.docx"
  else
    echo "Error: no output path given, and no sibling 'Resume - $NAME - <Role>.pdf' found in" >&2
    echo "       $IN_DIR to derive <Role> from. Pass the output path explicitly." >&2
    exit 1
  fi
fi

command -v pandoc >/dev/null 2>&1 || { echo "Error: pandoc not found." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 not found." >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

WORKDAY_MD="$TMP/out.workday.md"
python3 "$PY_HELPER" "$INPUT" "$WORKDAY_MD"

if [[ "$KEEP_MD" -eq 1 ]]; then
  KEEP_PATH="${OUTPUT%.docx}.workday.md"
  cp "$WORKDAY_MD" "$KEEP_PATH"
  echo "Wrote: $KEEP_PATH"
fi

pandoc "$WORKDAY_MD" -o "$OUTPUT" -f markdown+smart -t docx --standalone

echo "Wrote: $OUTPUT"
