---
name: housekeeping
description: "Clean up what finished threads leave on this machine: stale git worktrees and their local branches. Use when asked for housekeeping, a cleanup, or which worktrees can be removed."
---

# Housekeeping

Nothing is removed until the user accepts a dry-run report. Decide per worktree with the facts
below, and never remove a worktree whose branch has commits nobody pushed.

1. **Survey, changing nothing.** `git worktree list --porcelain` gives each worktree's path and
   branch; for each branch, `git status --porcelain` in that worktree and
   `git rev-list --count origin/main..<branch>` show uncommitted work and unmerged commits, and
   `gh pr list --head <branch> --state all --json number,state` shows its PR. Classify:
   - **Would remove**: the PR is merged or closed and the worktree is clean. Or the branch has no
     commits of its own beyond `origin/main` and the tree is clean.
   - **Kept, with the reason**: uncommitted changes, unpushed commits, an open PR, or the main
     checkout. Name every never-committed worktree too: a paused thread with no shell open looks
     exactly like a finished one, so those are where the user's eye is needed.

   Report the two lists, then stop. A request only to see what could be removed ends here.

2. **On acceptance**, remove only what the report listed: `git worktree remove <path>` (never
   `--force` on a worktree with changes), then `git branch -d <branch>` (never `-D`; a branch that
   git refuses to delete was not merged, so it is kept and reported). Skip any worktree the user
   spared.

3. Report what was removed as a count, anything an error stopped, and every kept worktree with its
   reason. A kept worktree is the user's call: name it and leave it.
