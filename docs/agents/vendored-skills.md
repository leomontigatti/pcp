# Skills started from upstream

Most of the skills in `.agents/skills/` started as copies of someone else's, and all of them are ours
now. A skill is edited like any other doc. Nothing compares the skills with upstream: no script, CI job
or schedule.

Until this port, `skills-lock.json` pinned the `mattpocock/skills` ones by content hash, installed with
the `skills` tool. That file was removed: an installer re-run would overwrite the local changes, and the
hash only says the copy is unchanged, which is no longer the rule. The lock's last state is in git
history at commit `ac69962`.

## Where each came from

| Skill                                                                                                                           | Upstream                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `code-review`, `codebase-design`, `diagnosing-bugs`, `domain-modeling`, `pr`, `prototype`, `tdd`, `to-spec`, `to-tickets`, `wayfinder` | [`mattpocock/skills`](https://github.com/mattpocock/skills) `skills/engineering/<name>`                                |
| `grilling`, `handoff`, `writing-for-agents`                                                                                     | `mattpocock/skills` `skills/productivity/<name>`                                                                      |
| `resolving-merge-conflicts`                                                                                                     | `mattpocock/skills`, which has since deleted it; kept because `babysit-pr` and `implementer` use it                    |
| `implement` (as `do-work`, with `ODOO-TDD.md`)                                                                                  | [`mattpocock/course-video-manager`](https://github.com/mattpocock/course-video-manager), reshaped after `implement` in `mattpocock/skills` |
| `implement-spec`                                                                                                                | `mattpocock/skills` `skills/engineering/implement-spec`, adapted from the start                                       |
| `babysit-pr`, `housekeeping`                                                                                                    | none: written here, first in en-escena and rewritten for pcp                                                          |

The copies in pcp were installed from `mattpocock/skills` before this port, and no upstream commit was
recorded for them; the `skills-lock.json` in git history lists their content hashes. The local
changes are listed below; the ones made while porting the agent setup from en-escena are the
Odoo and GitHub-only adaptations.

## Local changes

- `implement` runs `uv run just` recipes, not package-manager scripts. Its browser step is a scenario or a
  `dev-shell` snippet, since pcp has no browser tooling yet. Its DB notes are `ODOO-TDD.md`, written for
  `TransactionCase`. The frontend TDD notes are dropped: pcp's views are Odoo's, and no reducer or state
  machine pattern applies.
- `babysit-pr` waits on `gh pr checks --watch`, not a repo script, and has no CodeRabbit: pcp runs no
  external reviewer. Its verbs are the ones in `implement` step 5.
- `housekeeping` works from `git worktree` and `gh pr list`, with no sweep script and no per-worktree
  databases.
- `domain-modeling`, `to-spec`, `to-tickets`, `wayfinder` and `tdd` name `CONTEXT.md` where en-escena
  named `GLOSSARY.md`, and the GitHub tracker only.
- `code-review` names the pcp standards sources (`AGENTS.md`, `docs/agents/`, `CONTEXT.md`), and its
  correctness brief names Odoo's failure modes (record rules, `sudo()`, module upgrades, comprobante
  numbering and IVA).
- `pr` names the one-way doors of this repo: module upgrades and migrations, ARCA submissions, and writes
  that reach the deployed instance.
- `prototype` is kept as upstream, with its package-manager example replaced; its UI branch is written for a
  React app and is the least useful branch in pcp.
- The `agents/openai.yaml` files are the Codex skill metadata, kept as they came.

## Pulling an upstream change

Read the upstream diff since the commit above, port what is wanted by hand into our copy, keep our local
changes where the two conflict, and record the commit and date here. There is no installer to re-run.

## Not adopted

- `setup-matt-pocock-skills`: its output, [`issue-tracker.md`](./issue-tracker.md),
  [`triage-labels.md`](./triage-labels.md) and [`domain.md`](./domain.md), already exists.
- `triage`, `grill-me`, `grill-with-docs`, `improve-codebase-architecture`: rarely or never used, or covered
  by `grilling`, `domain-modeling` and `codebase-design`.
- `research`: the `research` agent (`.agents/agents/research.md`) does that job.
