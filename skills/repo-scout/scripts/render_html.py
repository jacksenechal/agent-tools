#!/usr/bin/env python3
"""Render a markdown file to HTML with Mermaid diagram support.

Usage: render_html.py <markdown-file> [output-html]

Uses marked.js (CDN) for markdown rendering, DOMPurify (CDN) to sanitize it, and
mermaid.js (CDN) for diagrams. No Python dependencies beyond stdlib.

The report quotes text from whatever repo was scouted, so its markdown is untrusted:
the title is HTML-escaped, the markdown is embedded so it cannot close the <script>
block, the rendered HTML is sanitized, Mermaid runs with securityLevel 'strict', and a
per-page Content Security Policy allows only the pinned scripts and the page's own inline
script, and blocks network requests.
"""
import base64
import hashlib
import html
import json
import sys
from pathlib import Path

# Exact versions with SRI (Subresource Integrity) hashes, so the browser refuses any file
# that differs from the one reviewed. To change one, follow references/upgrading-cdn-pins.md;
# scripts/verify_cdn_pins.py checks every entry against the npm registry tarball.
# (npm package, version, file within the package, sha384 integrity)
CDN_SCRIPTS = [
    ("marked", "15.0.12", "marked.min.js",
     "sha384-948ahk4ZmxYVYOc+rxN1H2gM1EJ2Duhp7uHtZ4WSLkV4Vtx5MUqnV+l7u9B+jFv+"),
    # 3.4.17 is under the 14-day minimum age: allowed as the first release patching
    # GHSA-cg2g-xh64-v4q7, GHSA-mrv2-3pqr-j5jr and GHSA-c6gr-qvv4-5v3f against 3.4.16.
    ("dompurify", "3.4.17", "dist/purify.min.js",
     "sha384-P0JNneQf81HOl9VwNXK76cQ9VMD6Nfsnepxb0cCOg8+UzEdzgPHAPV4wVQrvYQSx"),
    ("mermaid", "11.17.2", "dist/mermaid.min.js",
     "sha384-EOXBFmc3gx5mb+vn0vPvvGqACToJD24hhacX5Yx+8NUUQrHIle/Qi5Bg9o3zKwW2"),
]
CDN_BASE = "https://cdn.jsdelivr.net/npm"


def content_security_policy(inline_script):
    """Allow only the exact pinned CDN script URLs and this page's inline script. Images are limited to
    data: URIs and network requests are blocked, so injected markup cannot phone home. Inline
    styles stay allowed because Mermaid's SVG output uses them."""
    digest = base64.b64encode(hashlib.sha256(inline_script.encode()).digest()).decode()
    urls = " ".join(f"{CDN_BASE}/{pkg}@{ver}/{path}" for pkg, ver, path, _ in CDN_SCRIPTS)
    return (
        "default-src 'none'; "
        f"script-src {urls} 'sha256-{digest}'; "
        "style-src 'unsafe-inline'; img-src data:; font-src data:; "
        "base-uri 'none'; form-action 'none'"
    )


def script_tags():
    return "\n".join(
        f'<script src="{CDN_BASE}/{pkg}@{ver}/{path}" integrity="{sri}" crossorigin="anonymous"></script>'
        for pkg, ver, path, sri in CDN_SCRIPTS
    )

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{
    max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.65; color: #1a1a2e; background: #fafafa;
  }}
  h1 {{ border-bottom: 2px solid #333; padding-bottom: 0.3em; margin-top: 0; }}
  h2 {{ border-bottom: 1px solid #ddd; padding-bottom: 0.2em; margin-top: 2.5em; color: #2c3e50; }}
  h3 {{ margin-top: 1.8em; color: #34495e; }}
  blockquote {{
    border-left: 3px solid #7f8c8d; margin: 1em 0; padding: 0.5em 1em;
    background: #f0f0f0; color: #555; font-size: 0.95em;
  }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.92em; }}
  th, td {{ border: 1px solid #ddd; padding: 0.5em 0.75em; text-align: left; }}
  th {{ background: #ecf0f1; font-weight: 600; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  code {{
    background: #eef; padding: 0.15em 0.4em; border-radius: 3px;
    font-size: 0.88em; font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace;
  }}
  pre {{ background: #2d2d2d; color: #ccc; padding: 1em 1.2em; border-radius: 6px; overflow-x: auto; }}
  pre code {{ background: none; padding: 0; color: inherit; font-size: 0.85em; }}
  .mermaid-wrapper {{
    position: relative; margin: 1.5em 0;
  }}
  .mermaid {{
    text-align: center; background: #fff;
    padding: 1em; border-radius: 8px; border: 1px solid #e0e0e0;
  }}
  .expand-btn {{
    position: absolute; top: 0.4em; right: 0.4em; z-index: 1;
    background: #fff; border: 1px solid #ccc; border-radius: 4px;
    padding: 0.25em 0.5em; cursor: pointer; font-size: 0.8em; color: #555;
    opacity: 0.6; transition: opacity 0.15s;
  }}
  .expand-btn:hover {{ opacity: 1; }}
  .diagram-overlay {{
    display: none; position: fixed; inset: 0; z-index: 9999;
    background: rgba(255,255,255,0.97); overflow: auto;
    justify-content: center; align-items: center; padding: 2rem;
  }}
  .diagram-overlay.active {{ display: flex; }}
  .diagram-overlay .overlay-content {{
    width: 100%; height: 100%;
    display: flex; justify-content: center; align-items: center;
  }}
  .diagram-overlay .mermaid {{
    width: 95vw; height: 90vh; max-width: none;
    display: flex; justify-content: center; align-items: center;
    padding: 1em;
  }}
  .diagram-overlay .mermaid svg {{
    width: 100% !important; height: 100% !important;
    max-width: 100% !important; max-height: 100% !important;
  }}
  .diagram-overlay .close-btn {{
    position: fixed; top: 1rem; right: 1.5rem; z-index: 10000;
    background: #333; color: #fff; border: none; border-radius: 4px;
    padding: 0.4em 0.8em; cursor: pointer; font-size: 1em;
  }}
  .diagram-overlay .close-btn:hover {{ background: #555; }}
  dl {{ margin: 1em 0; }}
  dt {{ font-weight: 600; margin-top: 0.75em; }}
  dd {{ margin-left: 1.5em; margin-bottom: 0.25em; color: #444; }}
  hr {{ border: none; border-top: 1px solid #ddd; margin: 2em 0; }}
  a {{ color: #2980b9; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  @media print {{
    body {{ max-width: none; padding: 1cm; }}
    .mermaid {{ break-inside: avoid; }}
    h2 {{ page-break-before: always; }}
    h2:first-of-type {{ page-break-before: avoid; }}
  }}
</style>
</head>
<body>
<div id="content"></div>
{script_tags}
<script>{inline_script}</script>
</body>
</html>'''

# The page's only inline script. Its sha256 goes into the CSP, so nothing else inline can run.
INLINE_SCRIPT = '''const md = {markdown_json};

const renderer = new marked.Renderer();
const origCode = renderer.code.bind(renderer);
renderer.code = function(token) {{
  const text = typeof token === 'object' ? token.text : token;
  const lang = typeof token === 'object' ? token.lang : arguments[1];
  if (lang === 'mermaid') {{
    // Escape so the diagram source survives as text; mermaid reads it back via textContent.
    const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return '<div class="mermaid">' + escaped + '</div>';
  }}
  return origCode(token);
}};
marked.setOptions({{ renderer: renderer }});

// Sanitize before inserting: raw HTML in the markdown would otherwise run event handlers.
// Links from the scouted repo open in a new tab without leaking the opener or referrer.
DOMPurify.addHook('afterSanitizeAttributes', node => {{
  if (node.tagName === 'A' && node.hasAttribute('href')) {{
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }}
}});
document.getElementById('content').innerHTML = DOMPurify.sanitize(marked.parse(md), {{ FORBID_TAGS: ['style'] }});

// Wrap each .mermaid in a wrapper with an expand button
document.querySelectorAll('.mermaid').forEach(el => {{
  const wrapper = document.createElement('div');
  wrapper.className = 'mermaid-wrapper';
  el.parentNode.insertBefore(wrapper, el);
  wrapper.appendChild(el);

  const btn = document.createElement('button');
  btn.className = 'expand-btn';
  btn.textContent = 'Expand';
  btn.onclick = () => openOverlay(el);
  wrapper.appendChild(btn);
}});

// Create the fullscreen overlay (once)
const overlay = document.createElement('div');
overlay.className = 'diagram-overlay';
overlay.innerHTML = '<button class="close-btn">Close</button><div class="overlay-content"></div>';
document.body.appendChild(overlay);
overlay.querySelector('.close-btn').onclick = () => overlay.classList.remove('active');
overlay.addEventListener('click', e => {{ if (e.target === overlay) overlay.classList.remove('active'); }});
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') overlay.classList.remove('active'); }});

function openOverlay(mermaidEl) {{
  const content = overlay.querySelector('.overlay-content');
  content.innerHTML = '';
  const clone = mermaidEl.cloneNode(true);
  // Strip the old rendered id so mermaid re-renders at full size
  clone.removeAttribute('data-processed');
  clone.textContent = mermaidEl.getAttribute('data-original') || mermaidEl.textContent;
  content.appendChild(clone);
  overlay.classList.add('active');
  mermaid.run({{ nodes: [clone] }});
}}

// Stash the original mermaid source before mermaid renders it into SVG
document.querySelectorAll('.mermaid').forEach(el => {{
  el.setAttribute('data-original', el.textContent);
}});

// The report quotes text from whatever repo was scouted, so treat the markdown as untrusted:
// 'strict' makes Mermaid encode HTML in labels and disables click handlers.
mermaid.initialize({{ startOnLoad: true, theme: 'neutral', securityLevel: 'strict' }});
'''


def main():
    if len(sys.argv) < 2:
        print("Usage: render_html.py <markdown-file> [output-html]", file=sys.stderr)
        sys.exit(1)

    md_path = Path(sys.argv[1])
    html_path = Path(sys.argv[2]) if len(sys.argv) > 2 else md_path.with_suffix(".html")

    if not md_path.exists():
        print(f"Error: {md_path} not found", file=sys.stderr)
        sys.exit(1)

    content = md_path.read_text(encoding="utf-8")

    title = "Repo Scout Report"
    for line in content.splitlines():
        if line.startswith("# "):
            title = line.lstrip("# ").strip()
            break

    # Escape "<" so a "</script>" in the markdown cannot end the script block early.
    markdown_json = json.dumps(content).replace("<", "\\u003c")
    inline_script = INLINE_SCRIPT.format(markdown_json=markdown_json)
    page = HTML_TEMPLATE.format(
        title=html.escape(title),
        csp=content_security_policy(inline_script),
        script_tags=script_tags(),
        inline_script=inline_script,
    )
    html_path.write_text(page, encoding="utf-8")
    print(f"Rendered: {html_path}")


if __name__ == "__main__":
    main()
