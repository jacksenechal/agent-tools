#!/usr/bin/env bash
# Claude Code -> TTS adapter (Stop hook).
#
# Claude Code calls this on the Stop event with a JSON payload on stdin that
# contains `last_assistant_message` (and `transcript_path`, used as a fallback).
# We hand that text to the harness-agnostic `agent-speak` for playback.
#
# All harness-specific knowledge lives here; agent-speak stays generic.
# Fails open: any error exits 0 so it never blocks the session.

set -uo pipefail

# Master off switch without editing settings.json.
[ "${CLAUDE_TTS_DISABLE:-0}" = "1" ] && exit 0

payload="$(cat)"

# Prefer the final message from the hook input: the transcript file can lag
# behind the Stop event, so reading it here may return an earlier text block.
text="$(printf '%s' "$payload" | jq -r '.last_assistant_message // empty' 2>/dev/null)"

# Fallback for versions without last_assistant_message: the last assistant
# text in the transcript (content is an array of blocks; keep the text ones).
if [ -z "$text" ]; then
  transcript="$(printf '%s' "$payload" | jq -r '.transcript_path // empty' 2>/dev/null)"
  [ -z "$transcript" ] || [ ! -f "$transcript" ] && exit 0
  text="$(jq -rs '
    [ .[]
      | select(.type == "assistant")
      | .message.content
      | if type == "array"
        then ([ .[] | select(.type == "text") | .text ] | join(" "))
        else (. // "")
        end
    ]
    | map(select(. != ""))
    | last // empty
  ' "$transcript" 2>/dev/null)"
fi

# Lightweight firing log (confirms the hook runs on new sessions / debug
# silence). Disable with CLAUDE_TTS_LOG=0.
if [ "${CLAUDE_TTS_LOG:-1}" != "0" ]; then
  logdir="${XDG_STATE_HOME:-$HOME/.local/state}/agent-speak"
  mkdir -p "$logdir"
  printf '%s fired chars=%s\n' "$(date +%H:%M:%S)" "${#text}" >> "$logdir/hook.log"
fi

[ -z "$text" ] && exit 0

# agent-speak sits one level up from this script in the repo. Resolve through
# the install symlink so the hook works wherever the repo is checked out.
speak="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../agent-speak"

# Detach so playback never delays the prompt returning to the user.
printf '%s' "$text" | setsid "$speak" >/dev/null 2>&1 &
exit 0
