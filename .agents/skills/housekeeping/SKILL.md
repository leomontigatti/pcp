---
name: housekeeping
description: "Clean up what finished threads leave on this machine that T3's storage cleanup does not: local branches, and the worktrees it skips. Use when asked for housekeeping, a cleanup, or which worktrees or branches can be removed."
---

# Housekeeping

T3 Code's storage cleanup removes a thread's worktree on its own once the PR merges or the thread is
deleted, and keeps one with uncommitted changes (Settings → Storage; its "Last run" report names
each one kept and why). This skill sweeps what it leaves:

- **local branches**: T3 keeps the branch of every worktree it removes, so a resumed thread can
  recreate the checkout;
- **renamed worktrees**: one whose branch the session renamed, which T3 keeps as "repository or
  branch changed" (pingdotgg/t3code#16559);
- **unmanaged worktrees**: one outside T3's worktree folder, such as an implementer's under
  `.claude/worktrees/` that `implement-spec` did not remove, or one made by hand;
- **stack layers**: a worktree whose PR merged into another PR's branch rather than `main`, which T3
  does not count as merged.

Nothing is removed until the user accepts a dry-run report. Decide per entry with the facts below,
and never remove a worktree or branch with commits nobody pushed.

1. **Survey, changing nothing.** `git worktree list --porcelain` gives each worktree's path and
   branch, and `git branch --format='%(refname:short) %(worktreepath)'` the branches with no
   worktree. For each, `git status --porcelain` in its worktree and
   `git rev-list --count origin/main..<branch>` show uncommitted work and unmerged commits, and
   `gh pr list --head <branch> --state all --json number,state,baseRefName` shows its PR. Classify:
   - **Would remove**: the PR is merged or closed and the worktree, if any, is clean. Or the branch
     has no commits of its own beyond `origin/main` and the tree is clean.
   - **Kept, with the reason**: uncommitted changes, unpushed commits, an open PR, or the main
     checkout. Name every never-committed worktree too: a paused thread with no shell open looks
     exactly like a finished one, so those are where the user's eye is needed.

   Report the two lists, then stop. A request only to see what could be removed ends here.

2. **On acceptance**, remove only what the report listed: `git worktree remove <path>` (never
   `--force` on a worktree with changes), then `git branch -d <branch>` (never `-D`; a branch that
   git refuses to delete was not merged, so it is kept and reported). Skip any entry the user
   spared.

3. Report what was removed as a count, anything an error stopped, and every kept worktree or
   branch with its reason. A kept one is the user's call: name it and leave it.
