---
name: playwright-docker
description: >
  Dockerized Playwright + noVNC browser automation. Manages headless Chromium in Docker
  with persistent browser profiles, file upload support, and MCP integration.
  Use as the default browser automation tool for any task requiring web interaction,
  form filling, scraping, or automated browsing.
  Triggers on: "playwright setup", "playwright start", "playwright stop", "playwright status",
  "playwright login", "browser docker", "start browser", "browser automation setup".
---

# Playwright Docker Skill

Manages a Dockerized Playwright + noVNC browser for Claude Code automation. This provides
headless Chromium in Docker with a visual noVNC interface, persistent login sessions, and
full file upload support via `mcp__playwright__` tools.

**Assets location**: `~/workspace/agent-tools/skills/playwright-docker/assets/`

## Architecture

- **Docker container** (`playwright-display`): Runs Chromium + Microsoft Playwright MCP server + noVNC
- **MCP connection**: Claude Code connects via `mcp__playwright__` tools (stdio → SSE proxy)
- **Profile volume** (`playwright-profile`): Persists browser sessions across restarts
- **noVNC**: http://localhost:6080 — watch or manually interact with the browser in real time

## Sub-Commands

### `setup` — First-time setup

Run once to start the container and wire up the MCP server in Claude Code.

#### 1. Start the container

```bash
export RESUME_REPO_PATH=~/workspace/resume   # or adjust to your resume repo path
cd ~/workspace/agent-tools/skills/playwright-docker/assets
docker compose up -d
```

Verify it's running:
```bash
docker ps | grep playwright-display
```

noVNC should be accessible at http://localhost:6080.

#### 2. Add the MCP server (user-scoped, persists across all projects)

```bash
claude mcp add --scope user playwright -- docker run --rm -i --network=playwright-network ghcr.io/xtr-dev/mcp-playwright-novnc:latest mcp-proxy http://playwright-display:3080/sse
```

This connects Claude Code to the long-running container via a stdio-to-SSE proxy. Tools
will be available as `mcp__playwright__browser_*`.

#### 3. Log into sites (one-time per site)

Open http://localhost:6080. In the noVNC view, manually navigate and log in to any sites
you want the browser to stay authenticated to (e.g. LinkedIn). Sessions persist in the
`playwright-profile` Docker volume across container restarts.

**The agent NEVER handles credentials — you always type them yourself in the noVNC window.**

#### 4. Verify

Call `mcp__playwright__browser_navigate` to `https://google.com` and confirm
`mcp__playwright__browser_snapshot` returns content.

---

### `start` — Start the container

```bash
export RESUME_REPO_PATH=~/workspace/resume
cd ~/workspace/agent-tools/skills/playwright-docker/assets
docker compose up -d
```

### `stop` — Stop the container

```bash
cd ~/workspace/agent-tools/skills/playwright-docker/assets
docker compose down
```

This preserves the `playwright-profile` volume (sessions intact).

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

### `reset-session` — Clear browser profile (re-login required)

```bash
cd ~/workspace/agent-tools/skills/playwright-docker/assets
docker compose down -v   # deletes playwright-profile volume
docker compose up -d
```

Use this if sessions become corrupted or you need a clean slate.

### `login <site>` — Log into a site manually

1. Ensure container is running (`/playwright-docker status`)
2. Open http://localhost:6080 in your browser
3. In the noVNC window, the agent navigates to `<site>/login`
4. You type your credentials in the noVNC window
5. Session is saved to the `playwright-profile` volume automatically

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

docker compose up -d      # Start (preserves profile volume)
docker compose restart    # Restart (preserves profile volume)
docker compose down       # Stop (preserves profile volume)
docker compose down -v    # Stop AND delete profile volume (resets all sessions)
```

---

## Requirements

- Docker and Docker Compose
- ~2GB disk for the image (`ghcr.io/xtr-dev/mcp-playwright-novnc:latest`)
- ~1GB RAM while running
- Port 6080 (noVNC) and 3080 (MCP SSE) available locally
