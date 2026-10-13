#!/usr/bin/env bash
#
# SessionStart hook, wired from both `.claude/settings.json` and `.codex/hooks.json`. Both
# harnesses add a SessionStart hook's `hookSpecificOutput.additionalContext` to the session's
# context.
#
# Warns at the start of a session whose shell cannot find uv, docker or gh. The harness inherits
# PATH from the desktop login session, which reads `~/.profile`, not `~/.bashrc`, so a directory
# added only in `~/.bashrc` (uv lives in `~/.local/bin`) is missing from an agent's shell. Agents
# that prefix every command with `export PATH=...` hide that cause from the next session. The hook
# only reports: it never edits PATH, so the fix stays at the source.
#
# See docs/agents/agent-configuration.md#the-agent-shells-path.

set -uo pipefail

missing=()
for tool in uv docker gh jq; do
  command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done

if [ "${#missing[@]}" -eq 0 ]; then
  exit 0
fi

message="This session's shell cannot find ${missing[*]} on PATH. The harness inherits PATH from the desktop login session, so a tool directory added only in ~/.bashrc is missing here (uv lives in ~/.local/bin). Do not prefix commands with \`export PATH=...\`: tell the user, who fixes it at the source as docs/agents/agent-configuration.md#the-agent-shells-path says. Without uv, the Odoo commands in docs/agents/validation.md cannot run; say so instead of working around it."

# Printed without jq, so the warning needs nothing but bash. The message holds no double quote or
# backslash, the two characters JSON would need escaped.
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$message"
