---
name: playwright-docker
description: >
  Dockerized Playwright + noVNC browser automation. Manages headless Chromium in Docker
  with file upload support and MCP integration. Browser sessions are isolated (ephemeral).
  Use as the default browser automation tool for any task requiring web interaction,
  form filling, scraping, or automated browsing.
  Triggers on: "playwright setup", "playwright start", "playwright stop", "playwright status",
  "browser docker", "start browser", "browser automation setup".
---

# Playwright Docker Skill

Manages a Dockerized Playwright + noVNC browser for Claude Code automation. Built on
[xtr-dev/mcp-playwright-novnc](https://github.com/xtr-dev/mcp-playwright-novnc) (git
submodule) with minimal modifications for Claude Code compatibility.

**Assets location**: `~/workspace/agent-tools/skills/playwright-docker/assets/`

## Architecture

- **Docker container** (`playwright-display`): Runs Chromium + Microsoft Playwright MCP server + noVNC
- **MCP connection**: Claude Code connects via `mcp__playwright__` tools (stdio → SSE proxy)
- **noVNC**: http://localhost:6080/vnc.html — watch or manually interact with the browser in real time
- **Browser sessions are ephemeral** (`--isolated`): each MCP connection gets a fresh browser

### Upstream modifications

The upstream source lives in `assets/mcp-playwright-novnc/` as a **git submodule**. We
overlay two changes without modifying it:

1. **`--output-dir /tmp/.playwright-mcp`** (in `start-mcp.sh` mount) — Claude Code sends
   MCP `roots` with host filesystem paths that don't exist inside the container. Without
   this, the server tries to `mkdir` at those paths and fails with EACCES.
2. **Local image build** — the upstream GHCR package is private/unavailable, so
   `docker-compose.yml` uses `build: context: ./mcp-playwright-novnc` instead.

## Prerequisites

Before any sub-command, ensure the submodule is initialized and the image exists:

```bash
# Initialize submodule (no-op if already present)
cd ~/workspace/agent-tools
git submodule update --init skills/playwright-docker/assets/mcp-playwright-novnc

# Build image (uses cache if unchanged, safe to run repeatedly)
export RESUME_REPO_PATH=~/workspace/resume
cd ~/workspace/agent-tools/skills/playwright-docker/assets
docker compose build
```

## Sub-Commands

### `setup` — First-time setup

Run once to start the container and wire up the MCP server in Claude Code.

#### 1. Build and start the container

```bash
cd ~/workspace/agent-tools
git submodule update --init skills/playwright-docker/assets/mcp-playwright-novnc

export RESUME_REPO_PATH=~/workspace/resume
cd ~/workspace/agent-tools/skills/playwright-docker/assets
docker compose up -d --build
```

Verify it's running:
```bash
docker ps | grep playwright-display
```

noVNC is at http://localhost:6080/vnc.html. The browser itself does not launch until the
first MCP tool call.

#### 2. Add the MCP server (user-scoped, persists across all projects)

Check if already configured:
```bash
grep -q playwright ~/.claude.json && echo "already configured"
```

If not:
```bash
claude mcp add --scope user playwright -- docker run --rm -i --network=playwright-network mcp-playwright-novnc:local mcp-proxy http://playwright-display:3080/sse
```

Tools will be available as `mcp__playwright__browser_*`.

#### 3. Verify

Call `mcp__playwright__browser_navigate` to `https://google.com` and confirm
`mcp__playwright__browser_snapshot` returns content.

---

### `start` — Start the container

```bash
export RESUME_REPO_PATH=~/workspace/resume
cd ~/workspace/agent-tools/skills/playwright-docker/assets
docker compose up -d --build
```

### `stop` — Stop the container

```bash
cd ~/workspace/agent-tools/skills/playwright-docker/assets
docker compose down
```

### `restart` — Restart the container

```bash
cd ~/workspace/agent-tools/skills/playwright-docker/assets
docker compose restart
```

**Important**: After any restart, the MCP proxy holds a stale session ID. Either start a
new Claude Code conversation or run `/mcp` to reconnect.

### `status` — Check health

```bash
docker ps --filter name=playwright-display --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Also confirm MCP connectivity: `mcp__playwright__browser_navigate` to `https://google.com`.

### `update` — Pull upstream changes

```bash
cd ~/workspace/agent-tools
git submodule update --remote skills/playwright-docker/assets/mcp-playwright-novnc

export RESUME_REPO_PATH=~/workspace/resume
cd ~/workspace/agent-tools/skills/playwright-docker/assets
docker compose up -d --build
```

This pulls the latest upstream commit, rebuilds the image, and restarts the container.
After updating, reconnect the MCP server (new conversation or `/mcp`).

---

## Troubleshooting

### `MCP error -32603: HTTP 404: Session not found`

The MCP proxy has a stale session from before a container restart. Fix: start a new
conversation or run `/mcp` to reconnect. If that doesn't work, kill the stale proxy:

```bash
docker ps --filter "ancestor=mcp-playwright-novnc:local" --format "{{.ID}} {{.Command}}" | grep "mcp-" | awk '{print $1}' | xargs -r docker kill
```

Then reconnect via `/mcp`.

### `mcp__playwright__` tools not available

The MCP server isn't connected. Check:
1. Container running? `docker ps | grep playwright-display`
2. MCP configured? `grep playwright ~/.claude.json`
3. If both yes, run `/mcp` to reconnect.

### `EACCES: permission denied, mkdir`

The `--output-dir` workaround isn't active. Check that `start-mcp.sh` is mounted:
```bash
docker exec playwright-display cat /usr/local/bin/start-mcp.sh | grep output-dir
```

---

## Using the Browser Tools

Once set up, use `mcp__playwright__` tools in any skill or task:

| Tool | Purpose |
|------|---------|
| `mcp__playwright__browser_navigate` | Go to a URL |
| `mcp__playwright__browser_snapshot` | Capture accessibility tree (primary scraping method) |
| `mcp__playwright__browser_click` | Click an element |
| `mcp__playwright__browser_type` | Type into a field |
| `mcp__playwright__browser_press_key` | Press a key (Enter, ArrowDown, Tab, etc.) |
| `mcp__playwright__browser_select_option` | Select from standard `<select>` dropdown |
| `mcp__playwright__browser_file_upload` | Upload a file programmatically |
| `mcp__playwright__browser_take_screenshot` | Capture a screenshot |
| `mcp__playwright__browser_wait_for` | Wait for an element or condition |
| `mcp__playwright__browser_hover` | Hover over an element |

### File uploads

Use `browser_file_upload` with the container-internal path. The resume repo is mounted at
`/home/pwuser/resume/` (read-only), so for resume uploads:

```
/home/pwuser/resume/resume.pdf
```

### Form-filling gotchas

- **Lever combobox dropdowns**: Don't work with `browser_select_option`. Use click → `ArrowDown` → `Enter`.
- **Standard HTML `<select>`** (e.g., EEO fields): Use `browser_select_option` normally.
- **Location autocomplete**: Type city name only (e.g., "Portland"), wait for suggestions, `ArrowDown` + `Enter`.
- **Stale refs**: After each `browser_type` or `browser_click`, refs update. Always use refs from the most recent snapshot.

---

## Container Lifecycle

The container is configured with `restart: unless-stopped`, so it survives reboots.

```bash
cd ~/workspace/agent-tools/skills/playwright-docker/assets

docker compose up -d --build  # Start/rebuild
docker compose restart        # Restart (reconnect MCP after)
docker compose down           # Stop
```

---

## Requirements

- Docker and Docker Compose
- ~3GB disk for the locally-built image
- ~1GB RAM while running
- Port 6080 (noVNC) and 3080 (MCP SSE) available locally
