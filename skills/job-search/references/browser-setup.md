# Browser Automation Setup

This skill requires an MCP server providing Playwright-style browser tools
(`browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, etc.).

## Recommended: Dockerized Playwright (playwright-docker skill)

The `/playwright-docker` skill manages a Dockerized Playwright + noVNC browser with
persistent sessions and file upload support. It is the recommended setup for this skill.

Run `/playwright-docker setup` to configure it. Once set up:
- Tools are available as `mcp__playwright__browser_*`
- Resume uploads use `browser_file_upload`. Per-job résumés now live at `applications/<id>/Resume - <Name> - <Role>.pdf` in the jobs repo, so the jobs repo must be mounted into the container for programmatic upload (see the `playwright-docker` skill's mount notes). The resume repo's `/home/pwuser/resume/resume.pdf` is the canonical résumé only, not the tailored per-job one.
- LinkedIn and other sessions persist across container restarts
- Monitor automation in real time at http://localhost:6080

See the `playwright-docker` skill for full lifecycle management (start/stop/login/reset).

---

## Fallback: browsermcp

If you prefer not to run Docker, [browsermcp](https://browsermcp.com/) controls your real
desktop browser via Chrome DevTools Protocol.

**Limitations**: Cannot do file uploads (native OS dialogs are unreachable). Shares your
real browser session — automation and personal browsing are not isolated.

### Setup

1. Install the browsermcp Chrome extension from https://browsermcp.com/
2. Add to your Claude Code settings:

```bash
claude mcp add --scope user browsermcp -- npx @anthropic-ai/browsermcp@latest --browserName chrome
```

Tools will be prefixed `mcp__browsermcp__`. Add permissions in `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": ["mcp__browsermcp__*"]
  }
}
```

### File uploads with browsermcp

browsermcp cannot handle file uploads. When a form requires a resume upload, prompt the
user to upload manually.
