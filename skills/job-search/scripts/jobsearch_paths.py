"""Resolves the repo locations the job-search scripts work on.

Python twin of paths.sh; same resolution order, first hit wins:
  1. the environment variable (JOBS_REPO_PATH / RESUME_REPO_PATH accepted as aliases)
  2. ${XDG_CONFIG_HOME:-~/.config}/job-search/paths.env  (KEY=value lines)
  3. jobs_dir only: the git repo containing the current directory, if it has tracker.csv
  4. resume_dir only: a sibling of the jobs repo named `resume`

Never add a default that names a specific directory layout: that is what this module replaces.
"""

import os
import subprocess
import sys


def _config():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    path = os.path.join(base, "job-search", "paths.env")
    values = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.startswith("export "):
                    line = line[len("export "):]
                key, _, val = line.partition("=")
                values[key.strip()] = os.path.expanduser(val.strip().strip("'\""))
    except OSError:
        pass
    return values


def jobs_dir(required=True):
    d = (os.environ.get("JOBS_DIR") or os.environ.get("JOBS_REPO_PATH")
         or _config().get("JOBS_DIR"))
    if not d:
        try:
            top = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                 capture_output=True, text=True, check=True).stdout.strip()
            if os.path.isfile(os.path.join(top, "tracker.csv")):
                d = top
        except (OSError, subprocess.CalledProcessError):
            pass
    if not d and required:
        sys.exit("job-search: cannot find the jobs repo. Run from inside it, set JOBS_DIR, "
                 "or put JOBS_DIR=/path/to/jobs-repo in ~/.config/job-search/paths.env")
    return d


def resume_dir():
    d = (os.environ.get("RESUME_DIR") or os.environ.get("RESUME_REPO_PATH")
         or _config().get("RESUME_DIR"))
    if not d:
        jd = jobs_dir(required=False)
        sibling = jd and os.path.join(os.path.dirname(jd), "resume")
        if sibling and os.path.isdir(os.path.join(sibling, ".git")):
            d = sibling
    return d


def profile_field(field):
    """One value from the user's profile (<jobs repo>/profile.md): the Value cell of the
    `| <field> | <value> |` table row whose Field matches, case-insensitively. None if the
    profile or the row is missing. Personal values come from here, never from the skill."""
    jd = jobs_dir(required=False)
    if not jd:
        return None
    try:
        with open(os.path.join(jd, "profile.md"), encoding="utf-8") as f:
            for line in f:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 2 and cells[0].lower() == field.lower():
                    return cells[1] or None
    except OSError:
        pass
    return None
