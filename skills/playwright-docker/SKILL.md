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
[xtr-dev/mcp-playwright-novnc](https://github.com/xtr-dev/mcp-playwright-novnc) with
minimal modifications for Claude Code compatibility.

**Assets location**: `~/workspace/agent-tools/skills/playwright-docker/assets/`

## Architecture

- **Docker container** (`playwright-display`): Runs Chromium + Microsoft Playwright MCP server + noVNC
- **MCP connection**: Claude Code connects via `mcp__playwright__` tools (stdio → SSE proxy)
- **noVNC**: http://localhost:6080/vnc.html — watch or manually interact with the browser in real time
- **Browser sessions are ephemeral** (`--isolated`): each MCP connection gets a fresh browser

### Upstream modifications

Only two changes from upstream, both in the `start-mcp.sh` mount:

1. **`--output-dir /tmp/.playwright-mcp`** — Claude Code sends MCP `roots` with host
   filesystem paths that don't exist inside the container. Without this, the server tries
   to `mkdir` at those paths and fails with EACCES.
2. **Local image build** — the upstream GHCR package (`ghcr.io/xtr-dev/mcp-playwright-novnc`)
   is private/unavailable, so we build from the bundled source clone.

## Sub-Commands

### `setup` — First-time setup

Run once to start the container and wire up the MCP server in Claude Code.

#### 1. Build and start the container

```bash
export RESUME_REPO_PATH=~/workspace/resume   # or adjust to your resume repo path
cd ~/workspace/agent-tools/skills/playwright-docker/assets
docker compose up -d --build
```

Verify it's running:
```bash
docker ps | grep playwright-display
```

noVNC should be accessible at http://localhost:6080/vnc.html.

The browser does not launch until the first MCP tool call (e.g. `browser_navigate`).

**Important**: After restarting the container, you must restart your Claude Code conversation
(or reconnect the MCP server via `/mcp`) so the proxy gets a fresh session ID.

#### 2. Add the MCP server (user-scoped, persists across all projects)

```bash
claude mcp add --scope user playwright -- docker run --rm -i --network=playwright-network mcp-playwright-novnc:local mcp-proxy http://playwright-display:3080/sse
```

This connects Claude Code to the long-running container via a stdio-to-SSE proxy. Tools
will be available as `mcp__playwright__browser_*`.

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

### `status` — Check health

```bash
docker ps --filter name=playwright-display --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Also confirm MCP connectivity: `mcp__playwright__browser_navigate` to `https://google.com`.

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

The container is configured with `restart: unless-stopped`, so it survives reboots automatically.

```bash
# All management commands run from:
cd ~/workspace/agent-tools/skills/playwright-docker/assets

docker compose up -d --build  # Start/rebuild
docker compose restart        # Restart
docker compose down           # Stop
```

---

## Requirements

- Docker and Docker Compose
- ~3GB disk for the locally-built image
- ~1GB RAM while running
- Port 6080 (noVNC) and 3080 (MCP SSE) available locally
