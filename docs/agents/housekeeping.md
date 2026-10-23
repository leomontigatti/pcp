# Housekeeping

The per-worktree resources the shared `housekeeping` skill sweeps here: each worktree that ran
`uv run just dev-up` has a database, a filestore and maybe a container on the machine's dev stack,
all named from a key that derives from the worktree's path. T3 removes a worktree without running
anything, so they outlive it.

## List

`uv run just dev-ls` prints one tab-separated line per key:

```
key           status  database         filestore        container  worktree
146abe9b55ef  live    wt_146abe9b55ef  wt_146abe9b55ef  running    /home/poto/.t3/worktrees/pcp/chore-dev-stack-per-worktree
64915ed18279  orphan  wt_64915ed18279  wt_64915ed18279  exited     /home/poto/.t3/worktrees/pcp/t3-0a1b2c3d
```

`orphan` means the worktree recorded for the key (in the database's comment, else the container's
`pcp.worktree` label) no longer exists, or none was recorded. `-` marks a resource the key does not
have. A worktree T3 removed while its thread is only paused shows as `orphan` too: judge it by the
thread, as the skill's step 2 says, since `dev-up` in the recreated worktree would find the same
key and pick its database up again.

## Remove

`uv run just dev-rm <key>` removes one key's container, database (`wt_<key>`) and filestore, by
name, under the stack's lock. It refuses a key whose worktree still exists, so a sweep cannot take a
live worktree's data; from inside a worktree, `uv run just dev-rm` with no key removes its own. It
touches nothing else: not `proto`, not the test templates, not another key, and never Postgres
itself.

The shared stack (Postgres in compose project `pcp-dev`, the `pcp-dev_odoo-data` volume, the
`pcp-dev-odoo` image) is the machine's, not a worktree's: the sweep leaves it.
