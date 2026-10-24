# Archive

Skills and tools that are no longer active but kept for reference. Nothing here is
maintained or tested, and `scripts/check_no_hardcoded_paths.sh` does not check it.

## pi-swarm

Retired 2026-08-06: the author stopped using the pi agentic tooling.

It depends on external artifacts that are also retired, so it will not
work as-is if restored:

- the `agent-sandbox:latest` Docker image
- the `pi` binary
- `~/.config/keys/opencode.key`

Restoring it requires re-provisioning the `pi` ansible role, which is
archived in the dotfiles repo at `archive/roles/pi`.

## tts

Archived 2026-10-23: unused for a while and untested since. Local text-to-speech for agent
replies (Kokoro, with PipeWire audio ducking) plus a Claude Code Stop hook. See
[`tts/README.md`](tts/README.md). It may come back if it is needed again.
