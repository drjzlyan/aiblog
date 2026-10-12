#!/usr/bin/env bash
# One-shot setup on a fresh clone. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."

uv sync
uv run playwright install chromium 2>/dev/null || python3 -m playwright install chromium

[ -f .env ] || cp .env.example .env

# First-time identity: your Medium @handle (used for links and footers only;
# login itself happens once in the browser and is saved git-ignored).
if ! grep -q '^MEDIUM_HANDLE=@' .env 2>/dev/null || grep -q '^MEDIUM_HANDLE=@yourhandle' .env 2>/dev/null; then
  handle=""
  if [ -t 0 ]; then
    printf 'Medium @handle (e.g. @yourhandle): '
    read -r handle || true
  else
    echo "Non-interactive shell: keeping MEDIUM_HANDLE=@yourhandle — edit .env."
  fi
  handle="${handle:-@yourhandle}"
  if grep -q '^MEDIUM_HANDLE=' .env 2>/dev/null; then
    sed -i '' "s/^MEDIUM_HANDLE=.*/MEDIUM_HANDLE=${handle}/" .env 2>/dev/null \
      || sed -i "s/^MEDIUM_HANDLE=.*/MEDIUM_HANDLE=${handle}/" .env
  else
    printf 'MEDIUM_HANDLE=%s\n' "$handle" >> .env
  fi
  echo "Set MEDIUM_HANDLE=${handle} in .env"
fi

# Personal resume state is git-ignored; bootstrap it from the template.
[ -f STATE.md ] || { cp STATE.example.md STATE.md; echo "Created STATE.md from template."; }

# Migrate a session saved by the retired MCP server, if present.
if [ ! -f medium-session.json ] && [ -f mcp/medium-mcp-server/medium-session.json ]; then
  cp mcp/medium-mcp-server/medium-session.json medium-session.json
  echo "Migrated Medium session (no re-login needed unless it expired)."
fi

cat <<MSG

Setup done. Next:
  1. Read CLAUDE.md, STATE.md, ROADMAP.md (and the active roadmaps/<series>.md).
  2. Medium login: the first tools/medium_*.py run opens a browser window;
     log in once (session saved to medium-session.json, git-ignored).
  3. Work is documented in docs/WORKFLOW.md; automation in tools/.
MSG
