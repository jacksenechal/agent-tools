#!/usr/bin/env python3
"""Daily watchlist poller: new roles at companies Jack cares about.

Reads `strategy/watchlist.csv` in the jobs repo (company, ats, slug, reason,
contact), lists open jobs on each company's public Greenhouse/Ashby/Lever
board, filters to Jack's role families and US-remote/Bay-Area geography, and
reports postings that are not already in `tracker.csv` (any stage, including
archived rows) and not already reported via `data/watchlist-seen.json`.

Stdlib only (urllib), read-only against the jobs repo: this script never
edits tracker.csv. Companies with `ats=none` have no public board API and are
left for the weekly liveness/browser check instead.

Matching, in order:
    1. URL or ATS job id already present in tracker.csv (any stage) -> skip,
       not reported; it's already a live or archived row with this exact
       posting.
    2. Company + normalized title matches ANY tracker row (any stage),
       the URL is different:
         - matched row stage == closed -> REOPENED <id>. The reopen rule
           (SKILL.md, "Archiving") applies: reuse the research/résumé/gate/
           referral, re-add through `add`.
         - matched row stage in (rejected, withdrawn) -> PRIOR <stage> <id>.
           Surfaced to Jack, never auto-reopened or auto-added.
         - matched row is anything else (a live row: discovered through
           offer) -> MOVED <id>. Useful liveness signal (the posting moved
           ATS or got a new id/URL at the same company) but not a new find
           and not auto-added.
    3. Otherwise, and not already in the seen-state file -> reported as NEW.

Output: TSV to stdout - status, company, title, location, url, reason,
contact, matched_id (empty for NEW).

Usage:
    python3 watch_companies.py [--watchlist PATH] [--tracker PATH]
                                [--seen PATH] [--dry-run]

--dry-run prints matches without updating the seen-state file (use this for
a trial run; the real daily run omits it so reported postings aren't
reprinted tomorrow).
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import jobsearch_paths

# Defaults are relative to the jobs repo (resolved by jobsearch_paths at run time).
DEFAULT_WATCHLIST = "strategy/watchlist.csv"
DEFAULT_TRACKER = "tracker.csv"
DEFAULT_SEEN = "data/watchlist-seen.json"
USER_AGENT = "Mozilla/5.0 (compatible; job-search-watchlist/1.0)"
TIMEOUT_DEFAULT = 10

# Jack's role families. A title matches only if it carries a leadership
# word, OR is a staff/principal IC title in the platform/infra/SRE/DevOps
# family -- plain senior or mid IC titles are out even when they name one of
# those domains (e.g. "Senior Cluster Site Reliability Engineer", "Software
# Engineer - DevOps Platform" do NOT match; "Staff Site Reliability
# Engineer" does).
#
# (a) Leadership word, scoped to engineering: manager/director/head/VP/
#     vice-president paired with "engineering" somewhere in the same title
#     clause (either order; a dash still breaks the clause, which is what
#     keeps "Incident Response Manager - Product & Engineering" out, but a
#     comma doesn't, which is what lets in "Senior Manager, Site Reliability
#     Engineering - Infrastructure Platform" and "Manager, Web Engineering");
#     CTO bare (unambiguous); or "lead" used as an engineering role noun
#     (engineering lead, tech lead, TLM, FDE lead) rather than a bare
#     trailing "... Lead" on an IC title.
LEADERSHIP_PATTERNS = [
    r"\b(manager|director|head|vp|vice president)\b[^\-–|]*\bengineering\b",
    r"\bengineering\b[^\-–|]*\b(manager|director|head|vp|vice president)\b",
    r"\bcto\b",
    r"\bengineering lead\b",
    r"\btech lead\b",
    r"\btlm\b",
    r"\bfde lead\b",
]
LEADERSHIP_WORD_RE = re.compile("|".join(LEADERSHIP_PATTERNS), re.IGNORECASE)
# (b) staff/principal combined with platform, infrastructure, SRE/
#     reliability, or DevOps -- the "staff or principal platform/infra
#     only" rule. Neither qualifier alone is enough.
SENIOR_IC_QUALIFIER_RE = re.compile(r"\b(staff|principal)\b", re.IGNORECASE)
PLATFORM_INFRA_FAMILY_RE = re.compile(
    r"\bplatform\b|\binfrastructure\b|\bsre\b|\breliability\b|\bdevops\b",
    re.IGNORECASE,
)
# Non-software domains that happen to use "platform"/"infrastructure"/
# "manager" etc. in a facilities, finance, go-to-market, or PM sense.
DISQUALIFY_RE = re.compile(
    r"\bsox\b|\bgtm\b|\bav\b|audiovisual|finance|financial|revenue systems|"
    r"\bsales\b|marketing|\blegal\b|recruiting|talent acquisition|"
    r"\bhr\b|people (ops|operations)|data center (technician|hardware)|"
    r"\belectrical\b|\bmechanical\b|manufacturing|procurement|facilities|"
    r"construction|real estate|workplace|product manager|program manager|"
    r"project manager|technical program manager|\btpm\b|developer relations|"
    r"evangelist|\beducation\b|documentation|accounting|\bcapex\b|"
    r"data scientist|data science|sourcing|deals lead|\bfp&a\b|sustainability|"
    r"partnerships|packaging|semiconductor",
    re.IGNORECASE,
)


def title_matches(title):
    t = title or ""
    if DISQUALIFY_RE.search(t):
        return False
    if LEADERSHIP_WORD_RE.search(t):
        return True
    if SENIOR_IC_QUALIFIER_RE.search(t) and PLATFORM_INFRA_FAMILY_RE.search(t):
        return True
    return False

# US-remote or SF Bay Area only (strategy/leadership-search.md hard filter).
BAY_AREA_RE = re.compile(
    r"san francisco|bay area|oakland|berkeley|san jose|fremont|"
    r"redwood city|palo alto|mountain view|sunnyvale|santa clara|"
    r"menlo park|south san francisco|novato|san rafael|marin",
    re.IGNORECASE,
)
US_REMOTE_RE = re.compile(
    r"remote.*(united states|u\.s\.|usa|\bus\b)|"
    r"(united states|u\.s\.|usa)[\s,-]*remote|"
    r"\bremote\s*-\s*us\b|\bus[\s-]remote\b",
    re.IGNORECASE,
)
# A bare "Remote" with no country qualifier is treated as US-remote only if
# there's no other country name in the string (best-effort; ATS location
# strings are inconsistent). Non-US cities disqualify explicitly.
NON_US_HINT_RE = re.compile(
    r"london|paris|uk\b|canada|india|bengaluru|germany|berlin|spain|"
    r"australia|melbourne|toronto|ireland|dublin|singapore|emea|apac|"
    r"mexico|brazil|poland|netherlands",
    re.IGNORECASE,
)

FILLER_WORDS_RE = re.compile(
    r"\b(senior|sr|jr|junior|lead|ii|iii|iv|the)\b", re.IGNORECASE
)
PUNCT_RE = re.compile(r"[^a-z0-9 ]")


def normalize_title(title):
    t = (title or "").lower()
    t = PUNCT_RE.sub(" ", t)
    t = FILLER_WORDS_RE.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def location_ok(location):
    if not location:
        return False
    if BAY_AREA_RE.search(location):
        return True
    if US_REMOTE_RE.search(location):
        return True
    if "remote" in location.lower() and not NON_US_HINT_RE.search(location):
        return True
    return False


def fetch_json(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return None, f"network error: {e}"
    try:
        return json.loads(body), None
    except (ValueError, UnicodeDecodeError) as e:
        return None, f"unparseable JSON: {e}"


def list_greenhouse(slug, timeout):
    data, err = fetch_json(
        f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true", timeout
    )
    if err or data is None:
        return [], err
    out = []
    for j in data.get("jobs", []):
        out.append(
            {
                "title": j.get("title", ""),
                "location": (j.get("location") or {}).get("name", ""),
                "url": j.get("absolute_url", ""),
                "job_id": str(j.get("id", "")),
            }
        )
    return out, None


def list_ashby(slug, timeout):
    data, err = fetch_json(
        f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout
    )
    if err or data is None:
        return [], err
    out = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        out.append(
            {
                "title": j.get("title", ""),
                "location": j.get("location", ""),
                "url": j.get("jobUrl", "") or j.get("applyUrl", ""),
                "job_id": str(j.get("id", "")),
            }
        )
    return out, None


def list_lever(slug, timeout):
    data, err = fetch_json(f"https://api.lever.co/v0/postings/{slug}", timeout)
    if err or data is None:
        return [], err
    out = []
    for j in data:
        cats = j.get("categories") or {}
        out.append(
            {
                "title": j.get("text", ""),
                "location": cats.get("location", ""),
                "url": j.get("hostedUrl", ""),
                "job_id": str(j.get("id", "")),
            }
        )
    return out, None


LISTERS = {
    "greenhouse": list_greenhouse,
    "ashby": list_ashby,
    "lever": list_lever,
}


def load_watchlist(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_tracker(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def tracker_url_and_id_index(tracker_rows):
    """Map every URL / application_url and bare ATS job id seen in the
    tracker to its row, across every stage (archived rows included)."""
    by_url = {}
    by_id = {}
    for row in tracker_rows:
        for field in ("url", "application_url"):
            val = (row.get(field) or "").strip()
            if val:
                by_url[val] = row
        # Pull a trailing ATS job id / slug out of the URL too, so a posting
        # whose URL changed slightly (query string, host) can still match.
        for field in ("url", "application_url"):
            val = (row.get(field) or "").strip()
            m = re.search(r"([0-9a-fA-F-]{8,36}|\d{5,})(?:[/?#].*)?$", val)
            if m:
                by_id[m.group(1)] = row
    return by_url, by_id


def tracker_title_index(tracker_rows):
    """Map (company, normalized title) to its tracker row, across EVERY
    stage -- live rows included. A title match on a live row is not a new
    find (it's the same posting, possibly moved); a title match on an
    archived row is a reopen/prior-outcome case. See module docstring."""
    idx = {}
    for row in tracker_rows:
        key = (row.get("company", "").strip().lower(), normalize_title(row.get("role", "")))
        idx[key] = row
    return idx


def load_seen(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_seen(path, seen):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--watchlist", default=DEFAULT_WATCHLIST)
    ap.add_argument("--tracker", default=DEFAULT_TRACKER)
    ap.add_argument("--seen", default=DEFAULT_SEEN)
    ap.add_argument("--timeout", type=float, default=TIMEOUT_DEFAULT)
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print matches without updating the seen-state file",
    )
    args = ap.parse_args()

    # Defaults resolve against the jobs repo; explicit paths are taken as given.
    def resolve(p, default):
        if p == default:
            return os.path.join(jobsearch_paths.jobs_dir(), p)
        return os.path.expanduser(p)

    watchlist_path = resolve(args.watchlist, DEFAULT_WATCHLIST)
    tracker_path = resolve(args.tracker, DEFAULT_TRACKER)
    seen_path = resolve(args.seen, DEFAULT_SEEN)

    watchlist = load_watchlist(watchlist_path)
    tracker_rows = load_tracker(tracker_path)
    by_url, by_id = tracker_url_and_id_index(tracker_rows)
    title_idx = tracker_title_index(tracker_rows)
    seen = load_seen(seen_path)

    writer = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
    writer.writerow(
        ["status", "company", "title", "location", "url", "reason", "contact", "matched_id"]
    )

    new_seen_keys = []
    first = True
    for row in watchlist:
        ats = (row.get("ats") or "").strip().lower()
        if ats not in LISTERS:
            continue  # "none" companies: weekly browser check covers these.
        slug = (row.get("slug") or "").strip()
        company = (row.get("company") or "").strip()
        reason = (row.get("reason") or "").strip()
        contact = (row.get("contact") or "").strip()
        if not slug:
            continue

        if not first:
            time.sleep(args.delay)
        first = False

        jobs, err = LISTERS[ats](slug, args.timeout)
        if err:
            print(f"# {company}: error - {err}", file=sys.stderr)
            continue

        for job in jobs:
            title = job["title"]
            location = job["location"]
            url = job["url"]
            job_id = job["job_id"]

            if not title_matches(title):
                continue
            if not location_ok(location):
                continue

            if url in by_url or job_id in by_id:
                continue  # already a live or archived tracker row, same posting

            title_key = (company.lower(), normalize_title(title))
            matched = title_idx.get(title_key)
            seen_key = f"{company}::{ats}::{slug}::{job_id}"

            if matched is not None:
                stage = (matched.get("stage") or "").strip()
                if stage == "closed":
                    status = f"REOPENED {matched['id']}"
                elif stage in ("rejected", "withdrawn"):
                    status = f"PRIOR {stage} {matched['id']}"
                else:
                    # A live row (discovered..offer): same posting, moved ATS
                    # or got a new id/URL. Not a new find, not auto-added.
                    status = f"MOVED {matched['id']}"
                writer.writerow(
                    [status, company, title, location, url, reason, contact, matched["id"]]
                )
                new_seen_keys.append(seen_key)
                continue

            if seen_key in seen:
                continue

            writer.writerow(["NEW", company, title, location, url, reason, contact, ""])
            new_seen_keys.append(seen_key)

    if not args.dry_run:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for key in new_seen_keys:
            seen[key] = now
        save_seen(seen_path, seen)


if __name__ == "__main__":
    main()
