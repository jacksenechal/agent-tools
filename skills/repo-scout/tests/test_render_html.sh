#!/usr/bin/env bash
# Renders a hostile report and loads it in headless Chrome. Passes when the page rendered
# (markdown and a Mermaid diagram, which also proves the pinned scripts passed their SRI
# checks) and no injected payload ran (each one would set document.title to PWNED-*).
# Needs network access for the CDN scripts and a Chrome or Chromium binary ($CHROME overrides).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chrome="${CHROME:-$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)}"
[[ -n "$chrome" ]] || { echo "no Chrome/Chromium found; set CHROME" >&2; exit 2; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
python3 "$here/../scripts/render_html.py" "$here/hostile-report.md" "$tmp/report.html" >/dev/null
"$chrome" --headless=new --disable-gpu --no-sandbox --virtual-time-budget=10000 \
  --dump-dom "file://$tmp/report.html" 2>/dev/null > "$tmp/dom.html"

fail=0
check() { if grep -q "$2" "$tmp/dom.html"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }
check "markdown rendered" '<strong>bold</strong>'
check "mermaid diagram rendered" '<svg[^>]*id="mermaid'
check "title escaped, no payload ran" '<title>Report &lt;/title&gt;'
exit $fail
