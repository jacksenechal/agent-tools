#!/bin/bash
set -e

# Wait for X11 to be ready
sleep 2

# Calculate viewport size
VIEWPORT_WIDTH=$((${SCREEN_WIDTH:-1920} - 0))
VIEWPORT_HEIGHT=$((${SCREEN_HEIGHT:-1080} - 0))

echo "Starting Playwright MCP server..."
echo "  Port: ${MCP_PORT:-3000}"
echo "  Browser: ${MCP_BROWSER:-chromium}"
echo "  Display: ${DISPLAY:-:99}"
echo "  Viewport: ${VIEWPORT_WIDTH}x${VIEWPORT_HEIGHT}"

# --output-dir: Claude Code sends MCP roots with host filesystem paths that
# don't exist inside the container. Without this flag the server tries to mkdir
# at those paths and fails with EACCES. This overrides that behavior.
# See: https://github.com/microsoft/playwright-mcp/issues/1240#issuecomment-2888187192
exec node /app/cli.js \
    --port "${MCP_PORT:-3000}" \
    --host 0.0.0.0 \
    --browser "${MCP_BROWSER:-chromium}" \
    --config /etc/playwright-config.json \
    --allowed-hosts "*" \
    --viewport-size "${VIEWPORT_WIDTH}x${VIEWPORT_HEIGHT}" \
    --output-dir /tmp/.playwright-mcp \
    --isolated
