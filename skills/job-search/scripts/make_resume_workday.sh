#!/bin/bash
#
# make_resume_workday.sh — render a résumé markdown file to a plain, single-column .docx
# aimed at Workday's "Autofill with Resume" parser, which mangles the styled house-style PDF
# (make_resume_pdf.sh). Same source markdown, different render target.
#
# Usage:
#   make_resume_workday.sh <input.md> [output.docx] [--name "..."] [--keep-md] \
#       [--skills-style flat|categorized] [--keep-summary] [--phone "..."] \
#       [--edu-start YEAR] [--link URL]...
#
# This script is general-purpose and contains NO personal details. The applicant name must
# be supplied by the caller, via --name, $JOB_SEARCH_APPLICANT_NAME, or the "Full name" row of the
# user's profile.md in the jobs repo (read automatically). The script errors
# if no name is given. --phone, --edu-start, and --link work the same way: values come from the
# caller (profile.md), never hardcoded here.
#
# Defaults:
#   output.docx -> same dir as input, named "Resume - <Name> - <Role>.docx", where <Role> is
#                  read off a sibling "Resume - <Name> - <Role>.pdf" in the input's directory
#                  (the file make_resume_pdf.sh already produced there). If no such PDF
#                  exists, <Role> cannot be derived and an explicit output path is required.
#   --name       -> $JOB_SEARCH_APPLICANT_NAME, then profile.md "Full name"
#   --keep-md    -> also write the intermediate cleaned markdown as "<output base>.workday.md"
#                   beside the docx (off by default).
#   --skills-style flat|categorized
#                -> "flat" (default): Skills section flattened into one comma-separated
#                   paragraph, category labels dropped (what Workday's structured Skills field
#                   wants). "categorized": render the source's own categorized "Label: a, b, c"
#                   lines as plain paragraphs (no Word list, no bold), each category kept on its
#                   own line. See resume_to_workday_md.py's process_skills_section.
#   --keep-summary -> emit the Summary section as its own "# Summary" block. OFF by default:
#                   Workday has no Summary field and was bleeding that text into the first job's
#                   Role Description (confirmed on a live Autofill test, 2026-10-05). Only pass
#                   this to re-test a tenant where that might behave differently.
#   --phone "..." -> override the contact block's Phone line (e.g. the cell, not the Google
#                   Voice number the public résumé carries). This docx is only the autofill
#                   input; make_resume_pdf.sh's styled PDF, with the public number, replaces the
#                   uploaded attachment right after autofill runs.
#   --edu-start YEAR -> prepend "YEAR - " to the Education entry's date line (e.g. "May 2003" ->
#                   "1998 - May 2003") so Workday's Education "From" year field has something to
#                   parse.
#   --link URL    -> (repeatable) append an extra contact-block hyperlink, e.g. a personal
#                   website missing from the source résumé. Contact URLs (LinkedIn, GitHub,
#                   website, and any --link) are rendered as real docx hyperlinks with the
#                   visible text set to the URL, since Workday's Websites extractor reads
#                   hyperlink targets, not visible text. LinkedIn URLs are normalized to the
#                   "www." form (bare "linkedin.com" doesn't match Workday's field).
#
# Transform: resume_to_workday_md.py (beside this script) rewrites the house-style résumé
# markdown into plain, single-column markdown — contact block as one item per line, section
# headers renamed to standard words and promoted to real headings, each job entry split into
# separate Job Title / Company / Location / Date lines with full month names, "Scope:"
# sub-lines de-italicized into a plain line with the "Scope:" label dropped, all bold/italic/
# link formatting stripped to plain text, em/en dashes to hyphens. It also drops a "Remote"
# location line, strips a title's " · <subtitle>" suffix, forces Company to "Self-employed" for
# an Independent/Consultant title, and drops non-job sections (Open Source Projects,
# Recommendations, any Experience entry with no parseable Company/Dates line) — all learned from
# a live Workday "Autofill with Resume" test; see that script's module docstring for the full
# rule set and the multi-role-entry caveat. Any source line it couldn't fully normalize (e.g.
# a year-only date range with no month to expand) is reported to stderr as a NOTE — read those
# before trusting the output blindly.
#
# pandoc then renders that markdown straight to .docx, with smart quotes OFF (plain ASCII
# quotes — Workday's parser prefers them). Markdown headers become real Word Heading styles;
# nothing here introduces tables, columns, or text boxes.
#
# Why it's safe to drop sections here: this docx exists only to drive Workday's autofill, which
# then populates its own structured fields (work history, education, skills). The agent replaces
# the uploaded attachment with the full styled PDF (make_resume_pdf.sh output) right after
# autofill runs, so nothing dropped from this render is actually lost to the recruiter who
# reads the application. See the job-search skill's step 6a for that replace-the-attachment step.
#
# Requires: pandoc, python3.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_HELPER="$SCRIPT_DIR/resume_to_workday_md.py"

NAME="${JOB_SEARCH_APPLICANT_NAME:-}"
INPUT=""
OUTPUT=""
KEEP_MD=0
SKILLS_STYLE="flat"
KEEP_SUMMARY=0
PHONE=""
EDU_START=""
LINKS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)     NAME="$2"; shift 2 ;;
    --keep-md)  KEEP_MD=1; shift ;;
    --skills-style) SKILLS_STYLE="$2"; shift 2 ;;
    --keep-summary) KEEP_SUMMARY=1; shift ;;
    --phone)    PHONE="$2"; shift 2 ;;
    --edu-start) EDU_START="$2"; shift 2 ;;
    --link)     LINKS+=("$2"); shift 2 ;;
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
  source "$(dirname "${BASH_SOURCE[0]}")/paths.sh"
  NAME="$(jobsearch_profile_field "Full name")"
fi
if [[ -z "$NAME" ]]; then
  echo "Error: applicant name required. Pass --name \"...\", set \$JOB_SEARCH_APPLICANT_NAME," >&2
  echo "       or add a \"| Full name | ... |\" row to profile.md in your jobs repo." >&2
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
PY_ARGS=("$INPUT" "$WORKDAY_MD" --skills-style "$SKILLS_STYLE")
if [[ "$KEEP_SUMMARY" -eq 1 ]]; then
  PY_ARGS+=(--keep-summary)
fi
if [[ -n "$PHONE" ]]; then
  PY_ARGS+=(--phone "$PHONE")
fi
if [[ -n "$EDU_START" ]]; then
  PY_ARGS+=(--edu-start "$EDU_START")
fi
for link in "${LINKS[@]+"${LINKS[@]}"}"; do
  PY_ARGS+=(--link "$link")
done
python3 "$PY_HELPER" "${PY_ARGS[@]}"

if [[ "$KEEP_MD" -eq 1 ]]; then
  KEEP_PATH="${OUTPUT%.*}.workday.md"
  cp "$WORKDAY_MD" "$KEEP_PATH"
  echo "Wrote: $KEEP_PATH"
fi

# If the requested output is a .pdf, render to .docx first (same plain single-column
# layout Workday's parser wants), then convert that docx to PDF with LibreOffice headless.
# This exists for testing whether Workday's "Autofill with Resume" populates its structured
# Skills field from a plain PDF the way it does from a styled PDF, while keeping the
# work-experience-friendly plain layout this script already produces for .docx. LibreOffice's
# docx->pdf conversion preserves that plain layout (no reflow into columns/tables), so the PDF's
# text should read the same as the docx's when extracted with `pdftotext -layout`.
case "$OUTPUT" in
  *.pdf)
    DOCX_TMP="$TMP/render.docx"
    pandoc "$WORKDAY_MD" -o "$DOCX_TMP" -f markdown-smart -t docx --standalone
    command -v soffice >/dev/null 2>&1 || { echo "Error: soffice (LibreOffice) not found; cannot render .pdf output." >&2; exit 1; }
    soffice --headless --convert-to pdf --outdir "$TMP" "$DOCX_TMP" >/dev/null 2>&1
    CONVERTED="$TMP/$(basename "${DOCX_TMP%.docx}.pdf")"
    if [[ ! -f "$CONVERTED" ]]; then
      echo "Error: soffice did not produce a PDF." >&2
      exit 1
    fi
    mkdir -p "$(dirname "$OUTPUT")"
    cp "$CONVERTED" "$OUTPUT"
    ;;
  *)
    pandoc "$WORKDAY_MD" -o "$OUTPUT" -f markdown-smart -t docx --standalone
    ;;
esac

echo "Wrote: $OUTPUT"
