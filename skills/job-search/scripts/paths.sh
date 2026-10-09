# Resolves the repo locations the job-search scripts work on. Source it; do not execute it.
#
#   source "$(dirname "${BASH_SOURCE[0]}")/paths.sh"
#
# Sets and exports:
#   JOBS_DIR    the private job-search repo (tracker.csv, applications/, strategy/)  [required]
#   RESUME_DIR  the résumé repo (main + role/* archetypes)                            [optional]
#   SITE_DIR    the user's public website repo, a fact-check source                  [optional]
#
# Resolution order for each, first hit wins:
#   1. the environment variable (RESUME_REPO_PATH / JOBS_REPO_PATH accepted as aliases)
#   2. ${XDG_CONFIG_HOME:-$HOME/.config}/job-search/paths.env  (KEY=value lines)
#   3. JOBS_DIR only: the git repo containing the current directory, if it has tracker.csv
#   4. RESUME_DIR only: a sibling of JOBS_DIR named `resume`
#
# Never add a default that names a specific directory layout: that is what this file replaces.
# Call jobsearch_require_jobs_dir in scripts that cannot run without JOBS_DIR.

_js_config="${XDG_CONFIG_HOME:-$HOME/.config}/job-search/paths.env"

_js_from_config() {
  # $1 = key; prints the value from the config file, if any.
  [[ -f "$_js_config" ]] || return 0
  sed -n "s/^[[:space:]]*\(export[[:space:]]\{1,\}\)\{0,1\}$1=//p" "$_js_config" \
    | tail -n 1 | sed -e 's/^["'\'']//' -e 's/["'\'']$//' -e "s#^~#$HOME#"
}

JOBS_DIR="${JOBS_DIR:-${JOBS_REPO_PATH:-$(_js_from_config JOBS_DIR)}}"
if [[ -z "$JOBS_DIR" ]]; then
  _js_top="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  [[ -n "$_js_top" && -f "$_js_top/tracker.csv" ]] && JOBS_DIR="$_js_top"
fi

RESUME_DIR="${RESUME_DIR:-${RESUME_REPO_PATH:-$(_js_from_config RESUME_DIR)}}"
if [[ -z "$RESUME_DIR" && -n "$JOBS_DIR" && -d "$(dirname "$JOBS_DIR")/resume/.git" ]]; then
  RESUME_DIR="$(dirname "$JOBS_DIR")/resume"
fi

SITE_DIR="${SITE_DIR:-$(_js_from_config SITE_DIR)}"

export JOBS_DIR RESUME_DIR SITE_DIR
unset _js_top

jobsearch_require_jobs_dir() {
  if [[ -z "$JOBS_DIR" || ! -d "$JOBS_DIR" ]]; then
    echo "job-search: cannot find the jobs repo. Run from inside it, set JOBS_DIR, or put" >&2
    echo "  JOBS_DIR=/path/to/jobs-repo   in $_js_config" >&2
    return 2
  fi
}

jobsearch_require_resume_dir() {
  if [[ -z "$RESUME_DIR" || ! -d "$RESUME_DIR" ]]; then
    echo "job-search: cannot find the résumé repo. Set RESUME_DIR, put" >&2
    echo "  RESUME_DIR=/path/to/resume-repo   in $_js_config, or clone it beside the jobs repo as resume/" >&2
    return 2
  fi
}

# Reads one value from the user's profile ($JOBS_DIR/profile.md): the Value cell of the
# `| <field> | <value> |` table row whose Field matches (case-insensitive). Prints nothing if
# the profile or the row is missing. Personal values come from here, never from the skill.
#   name="$(jobsearch_profile_field "Full name")"
jobsearch_profile_field() {
  local profile="$JOBS_DIR/profile.md"
  [[ -n "$JOBS_DIR" && -f "$profile" ]] || return 0
  awk -F'|' -v want="$1" '
    NF >= 4 {
      key = $2; gsub(/^[ \t]+|[ \t]+$/, "", key)
      if (tolower(key) == tolower(want)) {
        val = $3; gsub(/^[ \t]+|[ \t]+$/, "", val); print val; exit
      }
    }' "$profile"
}
