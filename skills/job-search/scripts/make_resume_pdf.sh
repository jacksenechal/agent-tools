#!/bin/bash
#
# make_resume_pdf.sh — render a résumé markdown file to a styled PDF that matches the
# canonical résumé look (jacksenechal.com/resume house style).
#
# Usage:
#   make_resume_pdf.sh <input.md> [output.pdf] [--name "..."] [--source-url "..."]
#
# This script is general-purpose and contains NO personal details. The applicant name must
# be supplied by the caller, either via --name or the $JOB_SEARCH_APPLICANT_NAME env var
# (source it from your private profile, e.g. ~/workspace/jobs/profile.md). The script errors
# if no name is given. The name is used ONLY for the HTML page title (document metadata); the
# visible name/title on the page comes from the résumé markdown's own leading H1, exactly as
# in the canonical résumé.
#
# Defaults:
#   output.pdf   -> same dir/basename as input, with .pdf extension
#   --name       -> $JOB_SEARCH_APPLICANT_NAME (required if the flag is omitted)
#   --source-url -> "" (the print-footer "latest version at <url>" line is omitted if empty;
#                   supply your public résumé URL to reproduce the canonical footer). No dash
#                   in your value if your house style forbids em/en dashes.
#
# Styling:
#   The résumé CSS below is embedded verbatim from the resume repo's _pandoc/header_styles.html
#   so the script is self-contained and does not depend on the resume repo at runtime. Chrome's
#   headless print path activates the @media print block, which is what shapes the PDF (compact
#   type sizes, 92% body width, page-break-on-<hr>). A markdown horizontal rule (`---`) forces a
#   page break, matching the canonical _publish behavior.
#
# Toolchain mirrors the resume repo's _publish: pandoc -> HTML -> headless Chrome -> PDF.
# Requires: pandoc, and google-chrome-stable (or chromium / google-chrome).

set -euo pipefail

# No personal defaults here — name comes from --name or the env var (see header). Keep it that way.
NAME="${JOB_SEARCH_APPLICANT_NAME:-}"
SOURCE_URL=""
INPUT=""
OUTPUT=""

# --- arg parsing (positionals + flags, any order) ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)       NAME="$2";       shift 2 ;;
    --source-url) SOURCE_URL="$2"; shift 2 ;;
    -h|--help)    grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)
      if [[ -z "$INPUT" ]]; then INPUT="$1"
      elif [[ -z "$OUTPUT" ]]; then OUTPUT="$1"
      else echo "Unexpected arg: $1" >&2; exit 1
      fi
      shift ;;
  esac
done

if [[ -z "$INPUT" || ! -f "$INPUT" ]]; then
  echo "Error: input markdown file not found. Usage: $0 <input.md> [output.pdf] [--name ..] [--source-url ..]" >&2
  exit 1
fi
[[ -z "$OUTPUT" ]] && OUTPUT="${INPUT%.md}.pdf"

if [[ -z "$NAME" ]]; then
  echo "Error: applicant name required. Pass --name \"...\" or set \$JOB_SEARCH_APPLICANT_NAME" >&2
  echo "       (source it from your private profile, e.g. ~/workspace/jobs/profile.md)." >&2
  exit 1
fi

# --- locate a Chrome/Chromium binary ---
CHROME=""
for c in google-chrome-stable google-chrome chromium chromium-browser; do
  if command -v "$c" >/dev/null 2>&1; then CHROME="$c"; break; fi
done
if [[ -z "$CHROME" ]]; then echo "Error: no Chrome/Chromium binary found." >&2; exit 1; fi
command -v pandoc >/dev/null 2>&1 || { echo "Error: pandoc not found." >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- résumé styling, embedded from resume/_pandoc/header_styles.html (self-contained) ---
cat > "$TMP/header.html" <<'CSS'
<style type="text/css">
  /* Deterministic print margin. The canonical résumé relied on Chrome's implicit
     ~0.4in print default; newer Chrome headless defaults to ~1in, which narrows the
     text column and adds a page. Pin it so the PDF matches the canonical look on any
     Chrome version. Everything below is verbatim from resume/_pandoc/header_styles.html. */
  @page { margin: 0.4in; }
  /* Neutralize pandoc's default-template reader CSS (max-width:36em + 50px padding),
     which would otherwise pin the résumé to a narrow ~5in column. The resume repo avoids
     this by using its own minimal template via --data-dir; we stay self-contained and just
     override it here so the body honors the width rule below. */
  html, body { max-width: none !important; padding: 0 !important; }
  body { width: 73%; margin: auto; }
  body, p { font-family: Liberation Serif, Times New Roman, serif; font-size: 14pt; color: #000; }
  h1 { font-size: 40pt; font-weight: normal; text-transform: uppercase; margin: 1.3em 0 0; }
  h2 { font-size: 18pt; text-transform: uppercase; font-weight: bold;
    margin-top: 2em; margin-bottom: .4em; border-bottom: 1px solid black; }
  h3 { font-size: 15pt; font-weight: bold; margin-top: 1.1em; margin-bottom: .1em; }
  h4 { font-size: 14pt; font-weight: normal; margin-top: .1em; margin-bottom: .5em; }
  h5 { display: block; text-align: right; position: relative; font-weight: normal; margin-top: 0; font-size: inherit; color: inherit; }
  h5::before { content: "– "; }
  h1 + p { text-transform: uppercase; margin-bottom: 2em; }
  p { margin: 0.7em 0 0 0; color: #333; }
  ul { margin: .5em 0 0 0; list-style: none; padding-left: unset; }
  li { padding-left: 1em; text-indent: -1em; color: #333; }
  li:before { content: "•"; padding-right: 0.5em; }
  a { text-decoration: none; border-bottom: 1px dashed #bbb; color: #000; }
  a:hover, #foot a:hover { color: #444;  border-bottom: 1px dashed #444; }
  code { font-size: 10pt; background-color: #f4f4f4; padding: 2px; box-shadow: 1px 1px 2px #ddd; }
  #downloads { position: absolute; top: 1em; right: 1em; color: #777; font-style: italic; font-size: 10pt; }
  #online_resume { display: none; }
  #clear_foot { height: 3em; }
  hr { display: none; }

  @media print {
    body { width: 92%; margin: auto; }
    h1 { font-size: 20pt; margin-top: 0; }
    h2 { font-size: 12pt; margin-top: 2em; }
    h3 { font-size: 10pt; font-weight: bold; margin-top: 1.1em; margin-bottom: .1em; }
    h4 { font-size: 9pt; font-weight: normal; margin-top: .1em; margin-bottom: .5em; }
    body, p, li { font-size: 10pt; }
    code {font-size: 8pt; background-color: #eee; padding: 2px;}
    hr { display: block; page-break-after: always; padding: 0; margin: 0; border: 0; }
    a { text-decoration: none; border-bottom: none; color: inherit; }
    #downloads { display: none; }
    #online_resume { display: block; text-align: center; color: #777; font-style: italic; font-size: 10pt; }
  }
</style>
CSS

# --- optional print footer (canonical "latest version at <url>" line), only if a URL is given ---
esc() { printf '%s' "$1" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'; }
AFTER_ARGS=()
if [[ -n "$SOURCE_URL" ]]; then
  u="$(esc "$SOURCE_URL")"
  {
    printf '<div id="clear_foot"></div>\n'
    printf '<div id="online_resume">\n'
    printf '  The latest version of this document can be found at <a href="%s">%s</a>\n' "$u" "$u"
    printf '</div>\n'
  } > "$TMP/after.html"
  AFTER_ARGS=(--include-after-body="$TMP/after.html")
fi

pandoc "$INPUT" -o "$TMP/out.html" -t html5 -f markdown+smart --standalone \
  --email-obfuscation=references \
  --include-in-header="$TMP/header.html" \
  "${AFTER_ARGS[@]}" \
  --variable="pagetitle:Resume :: ${NAME}"

"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$OUTPUT" "$TMP/out.html" >/dev/null 2>&1

echo "Wrote: $OUTPUT"
if command -v pdfinfo >/dev/null 2>&1; then
  echo "Pages: $(pdfinfo "$OUTPUT" 2>/dev/null | awk '/^Pages/{print $2}')"
fi
