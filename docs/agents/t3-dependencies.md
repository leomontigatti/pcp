# T3 Code dependencies

What this repo's workflows assume about T3 Code. The global `t3-update-review`
skill reads this file after every T3 update; agents don't need it for everyday work.

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

### own-worktrees-only
- **Relies on:** T3 binds to a thread only the worktree T3 created for it: that worktree's
  branch and PR show on the thread and settle it on merge. A worktree the agent made itself
  gets neither. Basis: the rule in workflows; not checked in T3 source.
- **Used by:** `docs/agents/workflows.md` § Branches, worktrees and T3 Code threads;
  `.agents/skills/implement-spec/SKILL.md` § 2 Run the frontier (its exception).
- **Breaks if:** T3 stops binding the worktree it creates to its thread. The rule then keeps
  a constraint that no longer has a reason, so re-check it.

### thread-worktree-branch-rename
- **Relies on:** a session can rename the branch of its thread's worktree with `git branch -m`,
  and T3 keeps the thread on that worktree and does not rename the branch back. Basis: T3 issue
  pingdotgg/t3code#16559 describes a renamed branch that stays bound to its thread; T3 names
  generated branches `t3code/...`.
- **Used by:** `docs/agents/workflows.md` § Branches, worktrees and T3 Code threads
  (Branch prefixes).
- **Breaks if:** T3 reverts or refuses a branch name the session set, or finds the thread's
  worktree by branch name instead of by path.

### link-pr-to-thread
- **Relies on:** `link_pull_request` links a PR to the calling thread. The PR then shows its
  status on the thread, and the thread settles when the PR merges (`mcp/toolkits/pullRequests/tools.ts`,
  `LinkPullRequestTool`; the tool text asks to register every PR right after it is opened).
- **Used by:** `docs/agents/workflows.md` § Branches, worktrees and T3 Code threads (One thread,
  one branch, one PR); `.agents/skills/implement/SKILL.md` § 7 Open the PR and hand it off;
  `.agents/skills/implement-spec/SKILL.md` § 3 Merge each report, step 3 (the draft PR).
- **Breaks if:** `link_pull_request` is removed or renamed, or a linked PR no longer settles its
  thread when it merges.

### watch-pr-wakes
- **Relies on:** `watch_pull_request` watches an open PR for the calling thread, linking it
  first if needed, and wakes the session when a check fails, the required checks pass, someone
  else comments or reviews, or the branch starts to conflict. Only comments posted after the call
  wake it. The watch ends when the PR merges or closes, when the thread settles or is archived,
  after 8 failed reads in a row, when the user stops the thread, or on `unwatch_pull_request`;
  a settled thread must be unsettled before a new watch. A subagent cannot watch. While watched,
  the thread stays in the user's Working list; `unwatch_pull_request` returns it to the inbox
  (`mcp/toolkits/pullRequests/tools.ts`, `WatchPullRequestTool`, `UnwatchPullRequestTool`).
- **Used by:** `.agents/skills/babysit-pr/SKILL.md` § 2 Wait for the round, § 5 Report;
  `docs/agents/workflows.md` § Where work starts (last paragraph);
  `docs/agents/pull-requests.md` § Babysitting a PR.
- **Breaks if:** the tools are renamed or removed, a wake stops covering failed checks, comments
  or conflicts, or the watch stops lasting across pushes. The babysit would then wait on nothing.

### worktree-setup-script
- **Relies on:** a `t3.json` script with `runOnWorktreeCreate: true` runs in each new thread
  worktree (cwd is the worktree), with `T3CODE_PROJECT_ROOT` set to the main checkout, and
  `async: false` holds the agent until it exits (the default, `true`, starts the agent at once).
  T3 runs it only once it is imported into the project (Settings → Actions → Import from
  t3.json); `defaultThreadEnvMode` is read from the file without an import
  (`packages/contracts/src/t3ProjectFile.ts`; `packages/shared/src/projectScripts.ts`,
  `projectScriptRuntimeEnv`; `apps/server/src/project/ProjectSetupScriptRunner.ts`).
- **Used by:** `t3.json`; `docs/agents/workflows.md` § Branches, worktrees and T3 Code threads
  (first paragraph).
- **Breaks if:** T3 renames `runOnWorktreeCreate`, `async` or `T3CODE_PROJECT_ROOT`, changes the
  script's cwd, or flips the meaning of `async`.

### storage-cleanup-scope
- **Relies on:** T3's storage cleanup, as set on this machine (remove on merge and on thread
  delete, keep when "uncommitted-changes"), removes a thread's worktree with plain
  `git worktree remove` (no `--force`) once the thread is idle with no open terminal. That
  deletes ignored files (`.venv`) and unlinks the `prototype/.env` symlink without following it,
  so the main checkout's `.env` survives (tested with git outside the repo, 2026-10-14). It keeps
  the local branch. It skips a worktree whose branch changed, one outside its managed worktree
  folder, and one whose merged PR targeted a branch other than the default and whose head is not
  in it (`apps/server/src/storageCleanup.ts`, `cleanWorktrees`,
  `storageCleanupPullRequestMerged`).
- **Used by:** `.agents/skills/housekeeping/SKILL.md`; `docs/agents/workflows.md` § Branches,
  worktrees and T3 Code threads (last rule).
- **Breaks if:** cleanup starts deleting branches, uses `--force`, follows symlinks, or covers a
  case the housekeeping skill sweeps (it then has less to do), or stops covering one it skips.

### delegate-task-reviews
- **Relies on:** `delegate_task` takes `task`, `target` (`providerInstanceId`, `model`, model
  options), `role` (`review`, `research`), `mode: "async"`, `title` and `clientRequestId`
  (`mcp/toolkits/orchestrator/tools.ts`). An async child's result comes back as a
  notification to the calling thread, readable with `task_status` as `summary`. `task_cancel`
  stops a child.
- **Used by:** `.agents/skills/code-review/SKILL.md` § Spawning a reviewer;
  `docs/agents/agent-configuration.md` § Delegating to subagents (research).
- **Breaks if:** `delegate_task` renames or drops one of those inputs or roles, or an async
  child's result stops arriving as a notification. The review skill would then wait on nothing.

### agent-shell-path
- **Relies on:** T3 Code, the Claude Code and Codex sessions it starts, and its setup-script
  terminals inherit PATH from the desktop login session, which reads `~/.profile` and not
  `~/.bashrc`. Basis: the user's machine; not checked in T3 source.
- **Used by:** `docs/agents/agent-configuration.md` § The agent shell's PATH;
  `.agents/hooks/check-tool-path.sh` (SessionStart warning); `docs/agents/validation.md`
  (the `uv` commands); `t3.json` (`uv sync`).
- **Breaks if:** T3 changes how it starts agent sessions' environment, for example by reading a
  different profile file or setting its own PATH.

### session-hooks-loaded
- **Relies on:** the Claude Code and Codex sessions T3 starts load the project's hooks:
  `.claude/settings.json` (SessionStart, PostToolUse, Stop, PreToolUse) and `.codex/hooks.json`,
  with the worktree as the project directory. Codex asks once to trust them. Not checked in T3
  source; the workflow docs assume it.
- **Used by:** `docs/agents/agent-configuration.md` § Session hooks; `.claude/settings.json`;
  `.codex/hooks.json`; `.agents/hooks/stop-lint-check.sh`.
- **Breaks if:** T3 stops loading project hook files, or runs sessions without a project
  directory variable for the hook scripts to resolve.

## Watching

### renamed-branch-pr-lookup
- **Workaround:** the `link_pull_request` call after `gh pr create`, because T3's PR lookup
  misses a branch the agent renamed. Housekeeping also sweeps renamed worktrees by hand, since
  T3's cleanup skips them ("repository or branch changed").
- **Used by:** `docs/agents/workflows.md` § Branches, worktrees and T3 Code threads (One thread,
  one branch, one PR); `.agents/skills/housekeeping/SKILL.md` (what T3 leaves, step 1 Survey).
- **Would improve if:** T3 follows a renamed branch for PR lookup and worktree cleanup, so a
  renamed thread needs no link call and no hand sweep. Then the link call can be dropped
  (keep it if it stays harmless).
- **Watch:** pingdotgg/t3code#16559 (open).

### babysit-behind-base
- **Workaround:** `babysit-pr` reads `mergeStateStatus` on each wake and runs
  `gh pr update-branch` on BEHIND (step 4b). The watch does not wake on BEHIND, so a
  branch that falls behind with no other news stays unnoticed until the next wake.
- **Used by:** `.agents/skills/babysit-pr/SKILL.md` § 4b Bring the branch up to date.
- **Would improve if:** `watch_pull_request` wakes the session when the branch falls behind a
  base that requires it to be current.
- **Watch:** pingdotgg/t3code#17831 (open; PR not yet approved by maintainers).

### implementer-worktrees-by-hand
- **Workaround:** `implement-spec` runs each implementer as an Agent-tool worktree under
  `.claude/worktrees/`, outside T3's tracking. Each one is set up by hand (`ln -sf` of
  `prototype/.env`, then `uv sync --locked`): Agent-tool worktrees do not run `t3.json` scripts.
- **Used by:** `.agents/skills/implement-spec/SKILL.md` § 2 Run the frontier;
  `.agents/agents/implementer.md` step 2 Set it up.
- **Would improve if:** a `delegate_task` child with `isolation: "worktree"` can run the
  implementer role, has the project setup done before it starts, and reports its branch and head
  so the orchestrator can merge it. The tool text promises the setup; the merge flow is untested.
- **Watch:** `apps/server/src/mcp/toolkits/orchestrator/tools.ts` (`delegate_task`, `isolation`).

### ui-check-preview
- **Workaround:** the "What a user sees" check drives the flow with `uv run just scenarios` or
  `dev-shell`, reads the output back as text, and says which screens nobody looked at. The repo
  states it has no browser or screenshot tooling, so PR evidence is text only.
- **Used by:** `docs/agents/workflows.md` § What a user sees; `.agents/skills/implement/SKILL.md`
  § 4 Verify what a user sees; `.agents/skills/pr/SKILL.md` § Evidence;
  `docs/agents/pull-requests.md` § Evidence.
- **Would improve if:** the agent can open the local Odoo copy in T3's browser, log in, read it,
  and save a screenshot to attach to the PR. The preview toolkit is in 0.0.46-nightly.20261014.3105
  but has not been tried against `http://localhost:8069` or the login; once it has, this moves to
  Ready. Adopting would then mean: in `implement` § 4 and `workflows.md` § What a user sees, drive
  the local copy with `preview_navigate`, take a `preview_snapshot` with `save=true`, attach the
  path as `![alt](path)` in PR Evidence, and replace the "no screenshot tooling" lines in
  `pr/SKILL.md` and `pull-requests.md`, keeping the text check and the rule against the deployed
  instance.
- **Watch:** `apps/server/src/mcp/toolkits/preview/tools.ts` (`preview_navigate`,
  `preview_snapshot` with `save=true`, which returns a path to embed as an image).

## Ready

None yet.

## Resolved

### babysit-pr-wait
- **Workaround:** `gh pr checks <n> --watch --fail-fast` run as a background Bash call, which
  woke the session when it exited (`babysit-pr` step 2).
- **Used by:** `.agents/skills/babysit-pr/SKILL.md` § 2 Wait for the round;
  `docs/agents/workflows.md` § Where work starts (last paragraph);
  `docs/agents/pull-requests.md` § Babysitting a PR.
- **Would improve if:** T3 watches a PR for a thread and wakes the session on failed checks,
  passed checks, new comments and reviews, or conflicts, so no shell command is needed.
- **Watch:** `apps/server/src/mcp/toolkits/pullRequests/tools.ts` (`watch_pull_request`,
  `unwatch_pull_request`); pingdotgg/t3code#15057 (merged).
- **Met in:** 0.0.46-nightly.20261014.3105 (pingdotgg/t3code#15057) — **Adopting means:** in
  `babysit-pr` step 2, call `watch_pull_request` and end the turn; read the existing round first;
  `unwatch_pull_request` before the step 5 report; drop the `gh pr checks --watch` mentions in
  `workflows.md` and `pull-requests.md`. `gh pr checks --watch` stays for outside T3 and for
  checks still running after a wake. Now relied on as `watch-pr-wakes`.
- **Adopted:** 2026-10-14, leomontigatti/pcp#10.

### worktree-setup-by-hand
- **Workaround:** each new thread worktree got `prototype/.env` linked from the main checkout
  and `uv sync --locked`, run by hand before its first run (`workflows.md`).
- **Used by:** `docs/agents/workflows.md` § Branches, worktrees and T3 Code threads (first
  paragraph).
- **Would improve if:** T3 runs a project setup script in each new thread worktree, from a
  checked-in file, without a manual step per worktree.
- **Watch:** `packages/contracts/src/t3ProjectFile.ts` (`runOnWorktreeCreate`, `async`);
  `apps/server/src/project/ProjectSetupScriptRunner.ts`.
- **Met in:** 0.0.46-nightly.20261014.3105 (`t3.json` support at 3417bc3856a2) — **Adopting
  means:** a `t3.json` at the repo root whose `runOnWorktreeCreate` script links the `.env` and
  runs `uv sync --locked`, with `"async": false`; the user imports it once per install; the manual
  step leaves `workflows.md`. Now relied on as `worktree-setup-script`.
- **Adopted:** 2026-10-14, leomontigatti/pcp#10.

### housekeeping-worktrees
- **Workaround:** `housekeeping` classified and removed every finished worktree itself
  (`git worktree remove`, then `git branch -d`).
- **Used by:** `.agents/skills/housekeeping/SKILL.md`;
  `docs/agents/workflows.md` § Branches, worktrees and T3 Code threads (last rule);
  `docs/agents/vendored-skills.md` § Local changes (the `housekeeping` line).
- **Would improve if:** T3's storage cleanup removes finished worktrees on its own, with a
  report of what it kept and why, so the sweep only covers branches and the cases T3 skips.
- **Watch:** Settings → Storage; "Last run" report; pingdotgg/t3code#13836 (closed), #17563
  (merged 2026-10-10), #16559 (open: renamed-branch worktrees are skipped).
- **Met in:** 0.0.46-nightly.20261014.3105 (pingdotgg/t3code#17563) — **Adopting means:** turn
  on storage cleanup (done on this machine: on merge, on delete, keep when "uncommitted-changes"),
  then narrow `housekeeping` to local branches, renamed-branch worktrees, worktrees T3 does not
  manage, and stack layers T3 does not count as merged, keeping its no-unpushed-commits and
  no-`--force` rules. The `prototype/.env` link was checked: removal unlinks it and leaves the
  target. Now relied on as `storage-cleanup-scope`.
- **Adopted:** 2026-10-14, leomontigatti/pcp#10.
