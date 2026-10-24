#!/usr/bin/env python3
"""Verify the CDN pins in render_html.py against the npm registry.

Usage:
  verify_cdn_pins.py                          check every pin in CDN_SCRIPTS
  verify_cdn_pins.py --hash <pkg>@<ver> <path>  print the SRI hash for a candidate pin

For each file it downloads the package tarball from the npm registry, checks the tarball
against the registry's published sha512 integrity, hashes the file inside it, and checks
that the CDN serves the same bytes. The registry is the source of truth; the CDN is only a
mirror. It also asks the GitHub advisory database whether any advisory affects the
version (set GITHUB_TOKEN to avoid the anonymous rate limit). --hash also reports the
release age, so a candidate can be held to the minimum age in
references/upgrading-cdn-pins.md. Exits non-zero on a mismatch, an advisory, or (for
--hash) a release younger than the minimum age. Stdlib only.
"""
import base64
import datetime
import hashlib
import io
import json
import os
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_html import CDN_BASE, CDN_SCRIPTS

REGISTRY = "https://registry.npmjs.org"
ADVISORIES = "https://api.github.com/advisories?ecosystem=npm&affects={pkg}@{ver}"
MIN_AGE_DAYS = 14


def fetch(url, headers=None, attempts=3):
    """GET a URL, retrying transient network errors so one blip does not fail CI."""
    req = urllib.request.Request(url, headers=headers or {})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError):
            if attempt == attempts:
                raise
            time.sleep(5 * attempt)


def sri(data):
    return "sha384-" + base64.b64encode(hashlib.sha384(data).digest()).decode()


def registry_file(pkg, ver, path):
    """Return (file bytes, publish time) for a file in a package, verified against the registry."""
    meta = json.loads(fetch(f"{REGISTRY}/{pkg}"))
    dist = meta["versions"][ver]["dist"]
    tarball = fetch(dist["tarball"])
    algo, expected = dist["integrity"].split("-", 1)
    actual = base64.b64encode(hashlib.new(algo, tarball).digest()).decode()
    if actual != expected:
        raise ValueError(f"{pkg}@{ver}: tarball does not match the registry's {algo} integrity")
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as tar:
        try:
            data = tar.extractfile(f"package/{path}").read()
        except KeyError:
            raise ValueError(f"{pkg}@{ver}: {path} not found in the tarball") from None
    published = datetime.datetime.fromisoformat(meta["time"][ver].replace("Z", "+00:00"))
    return data, published


def advisories(pkg, ver):
    """Return "GHSA-id: summary" for each GitHub advisory affecting pkg@ver."""
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    found = json.loads(fetch(ADVISORIES.format(pkg=pkg, ver=ver), headers))
    return [f"{a['ghsa_id']}: {a['summary']}" for a in found]


def check(pkg, ver, path):
    """Return (registry SRI, CDN SRI, publish time)."""
    data, published = registry_file(pkg, ver, path)
    cdn = fetch(f"{CDN_BASE}/{pkg}@{ver}/{path}")
    return sri(data), sri(cdn), published


def main(argv):
    if argv[:1] == ["--hash"] and len(argv) == 3:
        pkg, _, ver = argv[1].rpartition("@")
        reg, cdn, published = check(pkg, ver, argv[2])
        age = (datetime.datetime.now(datetime.timezone.utc) - published).days
        print(f"{pkg}@{ver} {argv[2]}\n  published {published.date()} ({age} days ago)\n  {reg}")
        status = 0
        for adv in advisories(pkg, ver):
            print(f"  ADVISORY {adv}")
            status = 1
        if cdn != reg:
            print("  MISMATCH: the CDN serves different bytes than the registry tarball")
            status = 1
        if age < MIN_AGE_DAYS:
            print(f"  TOO NEW: under the {MIN_AGE_DAYS}-day minimum age")
            status = 1
        return status
    if argv:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2

    status = 0
    for pkg, ver, path, pinned in CDN_SCRIPTS:
        reg, cdn, _ = check(pkg, ver, path)
        advs = advisories(pkg, ver)
        ok = pinned == reg == cdn and not advs
        print(f"{'ok  ' if ok else 'FAIL'} {pkg}@{ver} {path}")
        if pinned != reg or reg != cdn:
            print(f"     pinned   {pinned}\n     registry {reg}\n     cdn      {cdn}")
        for adv in advs:
            print(f"     advisory {adv}")
        if not ok:
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
