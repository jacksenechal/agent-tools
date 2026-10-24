# Adds a pinned Chrome for Testing build on top of the upstream image, whose browser is
# whatever Playwright release it bundles. Both the golden browser and the isolated MCP
# sessions run this binary (CHROME_BIN, playwright-config.json).
#
# Pinned to Canary 158.0.8121.0, released 2026-10-24: an exception to the 14-day minimum
# age. It is the first build whose compiled-in Chrome Root Store drops emSign ECC Root
# CA - G3 (eMudhra key compromise, CVE-2026-111943 and CVE-2026-111944); Stable reaches
# that on 2026-10-27. Move to a Stable build at least 14 days old once one includes the
# removal. Google publishes no checksums for these downloads, so the hash below records
# what was downloaded over TLS from storage.googleapis.com and keeps rebuilds identical.
# See "Chrome for Testing pin" in SKILL.md for how to change it.
FROM base

ARG CHROME_VERSION=158.0.8121.0
ARG CHROME_SHA256=5819df33e5f0966504bde087f4d9cc36724d22e21eaa8408d8ecbae0e23657c7

USER root
RUN apt-get update && apt-get install -y --no-install-recommends unzip \
    && rm -rf /var/lib/apt/lists/* \
    && wget -q -O /tmp/chrome.zip \
       "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip" \
    && echo "${CHROME_SHA256}  /tmp/chrome.zip" | sha256sum -c - \
    && unzip -q /tmp/chrome.zip -d /opt/chrome-for-testing \
    && rm /tmp/chrome.zip \
    && /opt/chrome-for-testing/chrome-linux64/chrome --version

ENV CHROME_BIN=/opt/chrome-for-testing/chrome-linux64/chrome
USER pwuser
