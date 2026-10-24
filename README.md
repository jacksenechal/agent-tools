# agent-tools

Skills and small tools for AI coding agents, mainly Claude Code. A skill is a directory with
a `SKILL.md` file (instructions plus metadata) and any scripts, references, or assets it
needs. The agent loads a skill when a request matches its description.

## Contents

| Path | What it does |
|---|---|
| [`skills/playwright-docker`](skills/playwright-docker/SKILL.md) | Runs Chromium, two Playwright MCP (Model Context Protocol) servers, and a noVNC viewer in Docker, with a persistent logged-in "golden" session and isolated sessions that reuse its exported login state. |
| [`skills/repo-scout`](skills/repo-scout/SKILL.md) | Produces a short orientation report on an unfamiliar codebase (topology, entry points, architecture, trust boundaries, risk hotspots) with Mermaid diagrams, rendered to HTML. |
| [`skills/semi-formal-code-reasoning`](skills/semi-formal-code-reasoning/SKILL.md) | Structured templates for reasoning about code without running it: explicit premises, traced execution paths, and stated conclusions. Covers code questions, patch equivalence, and fault localization. |
| [`skills/skill-security-auditor`](skills/skill-security-auditor/SKILL.md) | Audits third-party agent skills by comparing what a skill says it does with what it can actually do, run in a sandboxed subagent so hostile content never reaches the main agent. |
| [`tts/`](tts/README.md) | Speaks agent replies aloud with a local TTS (text-to-speech) engine, Kokoro, and lowers other audio while it talks. Includes a Claude Code Stop hook. Not a skill; it has its own `install.sh`. |
| [`archive/`](archive/README.md) | Retired skills kept for reference. Not maintained. |

## Installing a skill

Clone the repo (the submodule is needed by `playwright-docker`), then link or copy a skill
directory into a skills folder your agent reads. For Claude Code that is `~/.claude/skills/`
for all projects, or `.claude/skills/` inside one project.

```bash
git clone --recurse-submodules https://github.com/jacksenechal/agent-tools.git
cd agent-tools
ln -s "$PWD/skills/repo-scout" ~/.claude/skills/repo-scout
```

A symlink keeps the skill updated with `git pull`. Some skills have setup steps of their own,
described in their `SKILL.md`.

## Standards

[`AGENTS.md`](AGENTS.md) sets the rules for every change here: no personal data, and no
hard-coded machine-specific paths. [`scripts/check_no_hardcoded_paths.sh`](scripts/check_no_hardcoded_paths.sh)
enforces the second rule. Run it before committing, or enable it as a pre-commit hook:

```bash
git config core.hooksPath .githooks
```

## How this is built

The code and docs are written with AI assistance and held to the standards in `AGENTS.md`.

## License

[MIT](LICENSE).
