#!/usr/bin/env bash
# Installs (or removes) the job-search orchestrator systemd user timers.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_SRC_DIR="$SCRIPT_DIR/../assets/systemd"
UNIT_DEST_DIR="$HOME/.config/systemd/user"

UNITS=(
  job-search-discover.service
  job-search-discover.timer
  job-search-liveness.service
  job-search-liveness.timer
  job-search-northbay.service
  job-search-northbay.timer
  job-search-network.service
  job-search-network.timer
)

ENABLE_TIMERS=(
  job-search-discover.timer
  job-search-liveness.timer
  job-search-northbay.timer
  job-search-network.timer
)

uninstall() {
  echo "Disabling timers..."
  systemctl --user disable --now "${ENABLE_TIMERS[@]}" || true

  echo "Removing unit files..."
  for unit in "${UNITS[@]}"; do
    rm -f "$UNIT_DEST_DIR/$unit"
  done

  systemctl --user daemon-reload
  echo "Uninstalled."
  exit 0
}

if [[ "${1:-}" == "--uninstall" ]]; then
  uninstall
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

echo "Installing unit files to $UNIT_DEST_DIR..."
for unit in "${UNITS[@]}"; do
  sed "s#@SKILL_DIR@#$SKILL_DIR#g" "$UNIT_SRC_DIR/$unit" > "$UNIT_DEST_DIR/$unit"
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
