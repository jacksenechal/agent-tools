# TTS: state and next steps

## Where we are

Local TTS for agent responses works in cold-CLI mode:

- Engine: `kokoro-tts` CLI (nazdridoy/kokoro-tts, via `uv tool`); model and voices in
  `$KOKORO_HOME` (default `~/.local/share/kokoro/`).
- Core: `agent-speak`, harness-agnostic; strips markdown, ducks other apps via
  PipeWire/`pactl`, one utterance at a time. Resolves `kokoro-tts` by absolute path
  (don't rely on PATH: hooks get a minimal PATH).
- Claude Code: `hooks/claude-stop-tts.sh` wired as a `Stop` hook. Logs each firing to
  `~/.local/state/agent-speak/hook.log`.
- Runtime toggle: `tts on|off|toggle|status|say TEXT` (mute flag at
  `~/.local/state/agent-speak/muted`). From a Claude Code prompt use `!tts off`.

## The open problem

Every utterance cold-loads the model and its imports, roughly 5 to 7 s before audio,
even for "hi". Synthesis itself is under 0.5 s. The fix is a warm persistent server.

## Decision made

Use an existing server rather than building and maintaining one:
[`remsky/Kokoro-FastAPI`](https://github.com/remsky/Kokoro-FastAPI) (maintained,
OpenAI-compatible `/v1/audio/speech`, streaming, CPU images, port 8880). Deploy it with
Docker, `--restart=always`, and a named volume for the model. Bonus: any harness with an
OpenAI-compatible TTS backend can point at the same `http://localhost:8880/v1`.

The PyTorch image is several GB; check free disk space first.

## Next steps

1. **Deploy the warm server:** `docker run -d --restart=always -p 127.0.0.1:8880:8880`
   with the CPU image; verify with `curl localhost:8880/v1/audio/speech`.
2. **Rewrite `agent-speak` as a thin client:** POST to localhost:8880 (streaming), pipe
   audio to the player through the existing ducking, and fall back to the cold
   `kokoro-tts` CLI when the server is down.
3. **Other harnesses:** point their OpenAI TTS backend's base URL at
   `http://localhost:8880/v1` and set a Kokoro voice.
4. **Install:** have `install.sh` set up the server too, so a new machine gets the warm
   path in one step.

## Verify after changes

- The Stop hook still fires: open a session, then check
  `~/.local/state/agent-speak/hook.log`.
- `tts say "hi"` still works (cold path).
