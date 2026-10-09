#!/usr/bin/env bash
# Orchestrator loop entry point. Invoked by systemd timers (job-search-discover.timer,
# job-search-liveness.timer, job-search-network.timer, plus any timers the user's jobs repo
# ships in ops/systemd/) or manually.
# See references/orchestrator-loop.md for the design this implements.
set -euo pipefail

usage() {
  echo "Usage: $(basename "$0") <discover|liveness|network|apply> [--force] [--dry-run]" >&2
  echo "       $(basename "$0") runbook <path in jobs repo> [--no-browser] [--force] [--dry-run]" >&2
}

MODE="${1:-}"
shift || true

# `runbook` runs a user-defined runbook from the jobs repo (e.g. a regional re-scout), with the
# same lock, log and browser preflight as the built-in modes. User-specific scheduled work lives
# in the jobs repo as a runbook plus its own timer (ops/systemd/), never as a mode here.
RUNBOOK=""
KIND="$MODE"
if [[ "$MODE" == "runbook" ]]; then
  RUNBOOK="${1:-}"
  shift || true
  [[ -n "$RUNBOOK" ]] || { usage; exit 2; }
fi

if [[ "$MODE" != "discover" && "$MODE" != "liveness" && "$MODE" != "network" && "$MODE" != "apply" && "$MODE" != "runbook" ]]; then
  usage
  exit 2
fi

FORCE=0
DRY_RUN=0
NO_BROWSER=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --no-browser) NO_BROWSER=1 ;;
    *)
      usage
      exit 2
      ;;
  esac
done

source "$(dirname "${BASH_SOURCE[0]}")/paths.sh"
jobsearch_require_jobs_dir || exit 2
if [[ -n "$RUNBOOK" ]]; then
  [[ -f "$JOBS_DIR/$RUNBOOK" ]] || { echo "runbook not found: $JOBS_DIR/$RUNBOOK" >&2; exit 2; }
  # Log, lock-fail and summary files are keyed by the runbook's name; behavior by KIND.
  MODE="$(basename "$RUNBOOK" .md)"
fi
LOCKFILE="$JOBS_DIR/.orchestrator.lock"
LOGFILE="$JOBS_DIR/orchestrator.log"
FAILCOUNT_FILE="$JOBS_DIR/.orchestrator-fails-$MODE"

mkdir -p "$JOBS_DIR"

log_line() {
  # $1=outcome $2=duration_seconds $3=exit_code
  printf '%s\t%s\t%s\t%ss\texit=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$MODE" "$1" "$2" "$3" >> "$LOGFILE"
}

START_TS=$(date +%s)

# Acquire an exclusive, non-blocking lock so overlapping runs (self or the other mode)
# bail out instead of colliding.
exec 200>"$LOCKFILE"
if ! flock -n 200; then
  log_line "skipped-lock" 0 0
  echo "skipped: lock held"
  exit 0
fi

# Random rest day: discovery only, skipped when --force is passed. Perfect daily
# regularity is more machine-like than occasional absence (see design doc).
if [[ "$KIND" == "discover" && "$FORCE" -eq 0 ]]; then
  if (( RANDOM % 7 == 0 )); then
    log_line "skipped-rest-day" 0 0
    echo "skipped: random rest day"
    exit 0
  fi
fi

# Golden browser preflight: discover/liveness/apply and runbooks need the logged-in session that
# lives in the playwright-display container. network mode touches no browser, so it skips this,
# as does a runbook run with --no-browser.
#
# NOTE: start-golden-browser.sh must NOT be invoked from the host. It runs INSIDE the
# container (it references /ms-playwright and /home/pwuser) and takes no arguments.
# The host-side way to bring the container up is docker compose in the playwright-docker
# skill's assets dir.
if [[ "$KIND" != "network" && "$NO_BROWSER" -eq 0 ]]; then
  # The playwright-docker skill normally sits beside this one; PW_ASSETS overrides.
  PW_ASSETS="${PW_ASSETS:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/playwright-docker/assets}"
  # The compose file binds both repos as volumes at their host paths, so both must be set.
  jobsearch_require_resume_dir || exit 2
  export RESUME_REPO_PATH="$RESUME_DIR" JOBS_REPO_PATH="$JOBS_DIR"

  browser_up() {
    docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "playwright-display"
  }

  if ! browser_up; then
    if [[ -f "$PW_ASSETS/docker-compose.yml" ]]; then
      echo "golden browser not running; starting via docker compose in $PW_ASSETS" >&2
      (cd "$PW_ASSETS" && docker compose up -d) || true

      # Bounded wait: the container needs time for X11 + supervisord + Chromium to come up.
      for _ in $(seq 1 15); do
        browser_up && break
        sleep 3
      done
    else
      echo "warning: no docker-compose.yml found at $PW_ASSETS" >&2
    fi

    if ! browser_up; then
      DURATION=$(( $(date +%s) - START_TS ))
      log_line "no-browser" "$DURATION" 3
      echo "error: golden browser (playwright-display) not running and could not be started" >&2
      exit 3
    fi
  fi
fi

case "$KIND" in
  discover) PROMPT="/job-search discover" ;;
  liveness) PROMPT="/job-search liveness" ;;
  network) PROMPT="/job-search network" ;;
  apply) PROMPT="/job-search apply" ;;
  runbook) PROMPT="Read $JOBS_DIR/$RUNBOOK and execute it end to end. Write a short summary of the run to $JOBS_DIR/.${MODE}-last-summary." ;;
esac

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "would run: claude -p \"$PROMPT\" --permission-mode acceptEdits (cwd=$JOBS_DIR)"
  exit 0
fi

set +e
(cd "$JOBS_DIR" && claude -p "$PROMPT" --permission-mode acceptEdits)
CLAUDE_EXIT=$?
set -e

DURATION=$(( $(date +%s) - START_TS ))

if [[ "$CLAUDE_EXIT" -eq 0 ]]; then
  log_line "ok" "$DURATION" "$CLAUDE_EXIT"
  echo 0 > "$FAILCOUNT_FILE"
  # Desktop alert with the run's one-line summary when the mode wrote one.
  SUMMARY_FILE="$JOBS_DIR/.${MODE}-last-summary"
  if [[ -s "$SUMMARY_FILE" ]] && command -v notify-send >/dev/null 2>&1; then
    notify-send "job-search $MODE" "$(cat "$SUMMARY_FILE")" || true
  fi
else
  log_line "failed" "$DURATION" "$CLAUDE_EXIT"
  FAILS=0
  [[ -f "$FAILCOUNT_FILE" ]] && FAILS=$(cat "$FAILCOUNT_FILE")
  FAILS=$(( FAILS + 1 ))
  echo "$FAILS" > "$FAILCOUNT_FILE"

  if [[ "$FAILS" -ge 3 ]]; then
    printf '%s\t%s\tALERT\tloop has failed 3 consecutive runs\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$MODE" >> "$LOGFILE"
    if command -v notify-send >/dev/null 2>&1; then
      notify-send "job-search orchestrator" "$MODE loop has failed 3 consecutive runs"
    fi
  fi
fi

exit "$CLAUDE_EXIT"
