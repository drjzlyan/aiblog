# Your custom setup (copy to CUSTOM.md — that file is git-ignored)

This repo works with zero configuration. Copy this file to `CUSTOM.md` at the
repo root and fill in whatever applies; the agent reads `CUSTOM.md` (if it
exists) at the start of every task and treats it as overrides.

## Account

- `MEDIUM_HANDLE`: your Medium @handle, e.g. `@yourhandle`
  (also set it in `.env`; only used for links and footers, login is via browser)

## Voice (overrides the default in docs/WORKFLOW.md)

- Audience:
- Tone:
-default: problem-first hook, short sections with "Why it matters", 8-12 min read
- Series footers on/off:

## Defaults

- Draft-first or ask-before-publish:
- Preferred tags per series:
- Topics to avoid:

## Your own MCP servers and skills

- This repo ships no MCP servers. To add yours, copy `.mcp.json.example` to
  `.mcp.json` (git-ignored) and register your servers there.
- To add your own skills, drop them in `.claude/skills/` (repo skills:
  `grilling`, `medium`). Mention them here so the agent prefers them:
- Extra instructions for the agent (always applied):
