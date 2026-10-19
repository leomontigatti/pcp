# T3 Code dependencies

What this repo's own workflows assume about T3 Code, beyond what the shared workflow's
`t3-dependencies.md` (in `leomontigatti/agent-workflow`, installed at `~/.agents/workflow`)
records for the shared skills. The `t3-update-review` skill reads both after every T3 update;
agents don't need this file for everyday work.

Checked against T3 Code at commit 3417bc3856a2 (installed 0.0.46-nightly.20261014.3105).
Entries cite `apps/server/...` and `packages/...` paths at that commit unless noted.

Status of an entry:
- **active**: we rely on T3 behaving this way; an update that changes it breaks us.
- **watching**: a workaround for something T3 can't do (yet), or a workflow T3
  could do natively better, faster or cheaper. "Would improve if" is the exact
  condition that lets us simplify.
- **ready**: the condition is met in the installed T3, but we haven't adopted it yet.
- **resolved**: adopted; kept as history.

## Active

### setup-links-env
- **Relies on:** the `runOnWorktreeCreate` script runs with the new worktree as its cwd and
  `T3CODE_PROJECT_ROOT` set to the main checkout, so it can link `prototype/.env` from there. A
  thread with no worktree runs no setup at all (pingdotgg/t3code#18891); the one case that runs the
  script in the main checkout itself is a thread launched as `existing_worktree` on the project
  root, which the script detects by comparing the two paths and then leaves `prototype/.env`
  alone. The script also runs
  `uv sync --locked`, so `uv` must be on the setup terminal's PATH
  (`packages/shared/src/projectScripts.ts`, `projectScriptRuntimeEnv`;
  `apps/server/src/project/ProjectSetupScriptRunner.ts`).
- **Used by:** `t3.json`; `docs/agents/workflows.md` § This repo's worktrees.
- **Breaks if:** T3 changes the script's cwd, stops setting `T3CODE_PROJECT_ROOT`, or runs the
  setup terminal without the login session's PATH.

### cleanup-unlinks-env
- **Relies on:** T3's storage cleanup removes a worktree with plain `git worktree remove` (no
  `--force`), which unlinks the `prototype/.env` symlink without following it, so the main
  checkout's `.env` survives (tested with git outside the repo, 2026-10-14)
  (`apps/server/src/storageCleanup.ts`, `cleanWorktrees`).
- **Used by:** `t3.json` (the symlink it creates); `docs/agents/workflows.md` § This repo's
  worktrees.
- **Breaks if:** cleanup starts following symlinks, or deletes the files a symlink points at.

### project-hooks-worktree-dir
- **Relies on:** the sessions T3 starts load this repo's own hooks (`.claude/settings.json`,
  `.codex/hooks.json`) with the thread's worktree as the project directory, so
  `$CLAUDE_PROJECT_DIR` or `git rev-parse --show-toplevel` resolves to the worktree and the Stop
  hook lints that worktree's changes. Not checked in T3 source.
- **Used by:** `.claude/settings.json`; `.codex/hooks.json`; `.agents/hooks/stop-lint-check.sh`;
  `docs/agents/agent-configuration.md` § Project hooks.
- **Breaks if:** T3 starts sessions in a directory other than the thread's worktree, or without a
  project directory variable for the hooks to resolve.

## Watching

### preview-odoo-login
- **Workaround:** `docs/agents/verification.md` § Drive falls back to `uv run just scenarios` and
  `dev-shell`, read back as text, because the preview tools have not been tried against the local
  Odoo copy (`http://localhost:8069`) and its login. Evidence shown in the thread is text until
  they have.
- **Used by:** `docs/agents/verification.md` § Drive and § Evidence.
- **Would improve if:** a session opens `http://localhost:8069` with `preview_open`, signs in as
  `admin`, drives a form and a printed report, and saves a `preview_snapshot` it can show in the
  thread. Then § Drive drops the fallback for screens, and § Evidence the "text until then" line. The
  shared `preview-tools-verification` trial covers the tools themselves.
- **Watch:** `apps/server/src/mcp/toolkits/preview/tools.ts` (`preview_open`, `preview_snapshot`
  with `save=true`).

## Ready

None yet.

## Resolved

None kept here: the entries this file used to carry for the shared skills (worktrees, PR linking
and watching, storage cleanup, `delegate_task`, the login shell's PATH) are the shared file's now.
