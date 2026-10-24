# Upgrading the CDN pins

`scripts/render_html.py` loads marked, DOMPurify and Mermaid from jsDelivr at exact versions,
each with an SRI (Subresource Integrity) hash in `CDN_SCRIPTS`. The browser refuses a file whose
hash does not match, so a compromised CDN or a tampered release cannot run in the report. The
cost is that upgrades are manual. This is the process.

## When

- **An advisory affects a pin.** `scripts/verify_cdn_pins.py` reports it, and CI runs that
  check weekly. Upgrade to the first patched version.
- **The pins are more than about six months old**, or the user asks. If you notice stale pins
  while running a scout, mention it at the end. Do not upgrade unasked mid-task.

## Rules

- **Minimum age 14 days.** Never pin a release younger than that: most malicious publishes
  are caught and pulled within days. The one exception is the first release that patches an
  advisory against the current pin. Record that exception in a comment beside the entry,
  naming the advisory IDs.
- **Stay within the major version** unless the user asks for a major upgrade. A major upgrade
  is its own change: read the migration notes, and expect to adjust the template's JavaScript
  (the `marked.Renderer` override is the most likely break).
- **One package per change**, so a regression points at one cause.
- **The npm registry is the source of truth.** The hash comes from the file inside the
  registry tarball, after the tarball matches the registry's own integrity hash. A CDN is
  only a mirror. Never copy a hash from a CDN page, a README, or another project.

## Steps

1. **Pick the candidate:** the newest release in the current major that is at least 14 days
   old. List the latest stable releases (no prereleases) with their dates:
   ```bash
   curl -s https://registry.npmjs.org/<pkg> | python3 -c 'import json,sys; t=json.load(sys.stdin)["time"]; [print(v, t[v][:10]) for v in [v for v in t if v[0].isdigit() and "-" not in v][-15:]]'
   ```
2. **Read the release notes** from the current pin up to the candidate. Look for anything a
   markdown renderer or sanitizer should not need: new network calls, new dependencies,
   obfuscated additions, a change of maintainers or repository. If something looks wrong,
   stop and tell the user.
3. **Get and check the hash:**
   ```bash
   python3 <skill-dir>/scripts/verify_cdn_pins.py --hash <pkg>@<version> <path-in-package>
   ```
   It must exit 0: tarball matches the registry, the CDN serves the same bytes, no advisories,
   old enough. A `TOO NEW` failure is acceptable only under the advisory exception above.
4. **Update the entry** in `CDN_SCRIPTS`: version and `sha384-...` hash.
5. **Verify and test:**
   ```bash
   python3 <skill-dir>/scripts/verify_cdn_pins.py
   <skill-dir>/tests/test_render_html.sh
   ```
   Then render a real report and open it: diagrams draw, the Expand overlay works, and the
   browser console shows no integrity or Content Security Policy errors (an SRI failure leaves
   the page blank).
6. **Commit** with the old and new versions and the release ages in the message.
