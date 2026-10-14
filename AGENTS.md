# PCP — guide for coding agents

Routes to the repo's conventions; each rule lives in the file a route names. The first section applies to
every task; a line in the second applies when its leading word matches the task.

Claude Code and Codex share this file, the skills in `.agents/skills/` and the hooks in `.agents/hooks/`
([agent-configuration.md](docs/agents/agent-configuration.md)). In Codex, "call the Skill tool with X" means
open `.agents/skills/X/SKILL.md` and follow it.

## Every task

- **Session conduct**: when a step needs no input from the user, keep going, and put status notes in the same
  message as the next action. Stop and ask only when the work cannot continue without them, or before anything
  destructive: deleting data, force-pushing, changing anything outside this repository, or anything that reaches
  ARCA or the deployed instance. When a rule in these docs fights the task, say so and get a sign-off before
  breaking it. End a run with what needs the user first, then what changed, then what was found in this run.
- **Implementing** (a feature, a fix, any code change): call the Skill tool with "implement" before editing. Where
  work starts, investigating before editing, and the thread's branch and worktree:
  [workflows.md](docs/agents/workflows.md).
- **Commands**: run only the recipes listed in the `justfile`, as `uv run just <recipe>`. [validation.md](docs/agents/validation.md)
  is the whole surface. A command the task needs that is not a recipe means adding the recipe first, not running it
  ad hoc.
- **Which instance**: recipes that talk to Odoo hit the **local** copy (`http://localhost:8069`). Never pass
  `--target deployed` or `--yes-deployed` unless the user asked for that run in so many words; the deployed instance
  carries the real CUIT and ARCA certificate, and its writes can reach ARCA. [validation.md](docs/agents/validation.md#which-instance)
  says what the flags do.
- **Subagents**: reviewers spawn as "Spawning a reviewer" in the `code-review` skill says, research as
  [agent-configuration.md](docs/agents/agent-configuration.md#delegating-to-subagents) says.
- **Vocabulary and decisions**: the terms are in [CONTEXT.md](CONTEXT.md), English names in code and Spanish where a
  user reads them; the decisions are in `docs/adr/`. Odoo addon conventions are enforced by the linters in
  `.pre-commit-config.yaml` (ruff, pylint-odoo, the OCA checks), so a rule they check needs no note here.

## When routed

- **Commands and the validation gate**: [validation.md](docs/agents/validation.md); `uv run just gate` before a
  commit is done.
- **What a user sees** (views, reports, printed documents), **documentation**: [workflows.md](docs/agents/workflows.md).
- **Pull requests**: [pull-requests.md](docs/agents/pull-requests.md).
- **Issues**, **PRDs**, **tickets**: [issue-tracker.md](docs/agents/issue-tracker.md);
  **triage labels**: [triage-labels.md](docs/agents/triage-labels.md).
- **Domain docs**: [domain.md](docs/agents/domain.md): `CONTEXT.md` and `docs/adr/`.
- **Agent configuration** (skills, hooks, subagent wiring):
  [agent-configuration.md](docs/agents/agent-configuration.md).
- **Upstream skills**: [vendored-skills.md](docs/agents/vendored-skills.md).
- **T3 Code dependencies** (a change to a workflow that leans on a T3 tool, setting or `t3.json`):
  [t3-dependencies.md](docs/agents/t3-dependencies.md); keep its entry's "Used by" true.
