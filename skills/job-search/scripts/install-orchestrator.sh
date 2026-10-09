#!/usr/bin/env bash
# Installs (or removes) the job-search orchestrator systemd user timers.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_SRC_DIR="$SCRIPT_DIR/../assets/systemd"
UNIT_DEST_DIR="$HOME/.config/systemd/user"

# Units come from two places: this skill's generic modes (assets/systemd/) and, for scheduled
# work unique to one user (a runbook run via `orchestrator.sh runbook <path>`), the user's jobs
# repo (ops/systemd/). Both are job-search-*.{service,timer} templates; @SKILL_DIR@ and
# @JOBS_DIR@ are filled in here. Every *.timer found is enabled.

installed_units() {
  local f
  for f in "$UNIT_DEST_DIR"/job-search-*.service "$UNIT_DEST_DIR"/job-search-*.timer; do
    [[ -e "$f" ]] && basename "$f"
  done
}

uninstall() {
  local units timers=() u
  mapfile -t units < <(installed_units)
  for u in "${units[@]}"; do [[ "$u" == *.timer ]] && timers+=("$u"); done
  echo "Disabling timers..."
  (( ${#timers[@]} )) && { systemctl --user disable --now "${timers[@]}" || true; }

  echo "Removing unit files..."
  for u in "${units[@]}"; do
    rm -f "$UNIT_DEST_DIR/$u"
  done

  systemctl --user daemon-reload
  echo "Uninstalled."
}

if [[ "${1:-}" == "--uninstall" ]]; then
  uninstall
  exit 0
fi

# Timers start with no useful working directory, so the jobs repo location must be recorded in
# the paths config. Run this from inside the jobs repo (or with JOBS_DIR set) the first time.
source "$SCRIPT_DIR/paths.sh"
jobsearch_require_jobs_dir || exit 2
PATHS_ENV="${XDG_CONFIG_HOME:-$HOME/.config}/job-search/paths.env"
if ! grep -qs '^[[:space:]]*\(export[[:space:]]\+\)\?JOBS_DIR=' "$PATHS_ENV"; then
  mkdir -p "$(dirname "$PATHS_ENV")"
  echo "JOBS_DIR=$JOBS_DIR" >> "$PATHS_ENV"
  [[ -n "$RESUME_DIR" ]] && echo "RESUME_DIR=$RESUME_DIR" >> "$PATHS_ENV"
  echo "Recorded repo locations in $PATHS_ENV"
fi

SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
mkdir -p "$UNIT_DEST_DIR"

# Start clean so a unit dropped from either source (e.g. a retired user runbook) goes away.
mapfile -t STALE < <(installed_units)
for u in "${STALE[@]}"; do
  [[ "$u" == *.timer ]] && { systemctl --user disable --now "$u" 2>/dev/null || true; }
  rm -f "$UNIT_DEST_DIR/$u"
done

echo "Installing unit files to $UNIT_DEST_DIR..."
ENABLE_TIMERS=()
for src in "$UNIT_SRC_DIR"/job-search-*.service "$UNIT_SRC_DIR"/job-search-*.timer \
           "$JOBS_DIR"/ops/systemd/job-search-*.service "$JOBS_DIR"/ops/systemd/job-search-*.timer; do
  [[ -e "$src" ]] || continue
  unit="$(basename "$src")"
  sed -e "s#@SKILL_DIR@#$SKILL_DIR#g" -e "s#@JOBS_DIR@#$JOBS_DIR#g" "$src" > "$UNIT_DEST_DIR/$unit"
  echo "  $unit  (from ${src%/*})"
  [[ "$unit" == *.timer ]] && ENABLE_TIMERS+=("$unit")
done

systemctl --user daemon-reload
systemctl --user enable --now "${ENABLE_TIMERS[@]}"

echo
echo "Installed. Current timers:"
systemctl --user list-timers 'job-search-*'

echo
echo "NOTE: these timers only fire while you have an active login session."
echo "To let them run when you're logged out (e.g. after reboot with no session), run:"
echo "  loginctl enable-linger \$USER"
