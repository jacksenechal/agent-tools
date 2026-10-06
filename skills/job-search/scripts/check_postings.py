#!/usr/bin/env python3
"""Cheap daily posting-liveness check against public ATS board APIs.

Checks every pre-applied tracker row (stage `discovered` through `ready_to_apply`)
whose `url` or `application_url` points at a Greenhouse, Ashby, or Lever job board,
and classifies it:

    open    - the board API confirms the posting is live.
    missing - the board API says the posting is gone (404 / not in the board's
              listed jobs). This is NOT the same as closed: see SKILL.md's
              liveness section, "Resolve before closing" -- the posting may have
              moved to the company's own careers page or another ATS before this
              row gets archived.
    unknown - a non-ATS URL, or a network/parse error. The run truly can't tell.

Stdlib only (urllib), read-only: this script never edits tracker.csv. It prints a
TSV report to stdout (or --out FILE): id, company, stage, ats, status, detail, url.

Usage:
    python3 check_postings.py [--tracker PATH] [--out PATH] [--timeout SECONDS]
"""

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request

DEFAULT_TRACKER = "~/workspace/jobs/tracker.csv"
PRE_APPLIED_STAGES = {
    "discovered",
    "researched",
    "resume_tailored",
    "application_prepped",
    "ready_to_apply",
}
USER_AGENT = "Mozilla/5.0 (compatible; job-search-liveness-check/1.0)"
TIMEOUT_DEFAULT = 10

GREENHOUSE_RE = re.compile(
    r"https?://(?:job-boards|boards)\.greenhouse\.io/([^/?#]+)/jobs/([^/?#]+)"
)
ASHBY_RE = re.compile(
    r"https?://jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-fA-F-]{36})"
)
LEVER_RE = re.compile(
    r"https?://jobs\.lever\.co/([^/?#]+)/([0-9a-fA-F-]{36})"
)


def fetch_json(url, timeout):
    """GET url, return (status_code, parsed_json_or_None, error_message_or_None)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            body = resp.read()
    except urllib.error.HTTPError as e:
        return e.code, None, f"HTTP {e.code}"
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return None, None, f"network error: {e}"
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError) as e:
        return status, None, f"unparseable JSON: {e}"
    return status, data, None


def detect_ats(url):
    """Return (ats_name, slug, job_id) for a recognized ATS URL, else None."""
    if not url:
        return None
    m = GREENHOUSE_RE.search(url)
    if m:
        return ("greenhouse", m.group(1), m.group(2))
    m = ASHBY_RE.search(url)
    if m:
        return ("ashby", m.group(1), m.group(2))
    m = LEVER_RE.search(url)
    if m:
        return ("lever", m.group(1), m.group(2))
    return None


def check_greenhouse(slug, job_id, timeout):
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}"
    status, data, err = fetch_json(api_url, timeout)
    if status == 200 and data is not None:
        return "open", api_url
    if status == 404:
        return "missing", api_url
    return "unknown", f"{api_url} ({err or f'HTTP {status}'})"


def check_ashby(slug, job_id, timeout):
    api_url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    status, data, err = fetch_json(api_url, timeout)
    if status == 404:
        # The whole board is gone -- the job is definitely not there, but we
        # can't tell if the company moved ATS entirely. Treat as missing, same
        # as a single posting 404 on Greenhouse/Lever.
        return "missing", api_url
    if status != 200 or data is None:
        return "unknown", f"{api_url} ({err or f'HTTP {status}'})"
    jobs = data.get("jobs") or []
    for job in jobs:
        if job.get("id") == job_id:
            return "open", api_url
    return "missing", api_url


def check_lever(slug, job_id, timeout):
    api_url = f"https://api.lever.co/v0/postings/{slug}/{job_id}"
    status, data, err = fetch_json(api_url, timeout)
    if status == 200 and data is not None:
        return "open", api_url
    if status == 404:
        return "missing", api_url
    return "unknown", f"{api_url} ({err or f'HTTP {status}'})"


CHECKERS = {
    "greenhouse": check_greenhouse,
    "ashby": check_ashby,
    "lever": check_lever,
}


def check_row(row, timeout):
    """Classify one tracker row. Prefers application_url when it is on a
    recognized ATS (that's usually the live apply link); falls back to url."""
    candidates = []
    au = (row.get("application_url") or "").strip()
    u = (row.get("url") or "").strip()
    if au:
        candidates.append(au)
    if u and u != au:
        candidates.append(u)

    ats_hit = None
    checked_url = None
    for c in candidates:
        hit = detect_ats(c)
        if hit:
            ats_hit = hit
            checked_url = c
            break

    if not ats_hit:
        return {
            "status": "unknown",
            "ats": "",
            "detail": "non-ATS URL",
            "url": au or u,
        }

    ats, slug, job_id = ats_hit
    status, detail = CHECKERS[ats](slug, job_id, timeout)
    return {"status": status, "ats": ats, "detail": detail, "url": checked_url}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tracker", default=DEFAULT_TRACKER,
                     help=f"path to tracker.csv (default: {DEFAULT_TRACKER})")
    ap.add_argument("--out", default=None, help="write TSV here instead of stdout")
    ap.add_argument("--timeout", type=float, default=TIMEOUT_DEFAULT,
                     help=f"per-request timeout in seconds (default: {TIMEOUT_DEFAULT})")
    ap.add_argument("--delay", type=float, default=0.3,
                     help="seconds to sleep between requests (politeness; default: 0.3)")
    args = ap.parse_args()

    import os
    tracker_path = os.path.expanduser(args.tracker)
    try:
        with open(tracker_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except OSError as e:
        print(f"error: could not read tracker at {tracker_path}: {e}", file=sys.stderr)
        sys.exit(1)

    out = open(args.out, "w", encoding="utf-8", newline="") if args.out else sys.stdout
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(["id", "company", "stage", "ats", "status", "detail", "url"])

    first = True
    for row in rows:
        if (row.get("stage") or "").strip() not in PRE_APPLIED_STAGES:
            continue
        if not first:
            time.sleep(args.delay)
        first = False
        result = check_row(row, args.timeout)
        writer.writerow([
            row.get("id", ""),
            row.get("company", ""),
            row.get("stage", ""),
            result["ats"],
            result["status"],
            result["detail"],
            result["url"],
        ])
        out.flush()

    if args.out:
        out.close()


if __name__ == "__main__":
    main()
