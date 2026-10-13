# Agent configuration

How Claude Code and Codex share this repo's instructions, skills, hooks and subagents, and how a
session delegates to a subagent.

## One copy, two harnesses

Claude Code and Codex read one copy of everything; only the wiring each harness insists on reading
from its own directory is kept per harness, and none of those files holds instructions of its own.

| What                   | The one copy                    | Claude Code reads it through                               | Codex reads it through                                      |
| ---------------------- | ------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------- |
| Repo instructions      | `AGENTS.md`                     | `AGENTS.md` directly (2.1.277+, only while no `CLAUDE.md` exists) | `AGENTS.md` directly                                 |
| Skills                 | `.agents/skills/<name>/`        | `.claude/skills`, a symlink to `.agents/skills`            | `.agents/skills` directly                                   |
| Hooks                  | `.agents/hooks/*.sh`            | the `hooks` block of `.claude/settings.json`               | `.codex/hooks.json`                                         |
| `research` subagent    | `.agents/agents/research.md`    | in T3, a `delegate_task` child; outside, `.claude/agents/research.md` | `.codex/agents/research.toml` (model)             |
| `reviewer` subagent    | `.agents/agents/reviewer.md`    | in T3, `delegate_task` children; outside, `reviewer-opus`  | `.codex/agents/reviewer.toml`, `reviewer-luna.toml` (model) |
| `implementer` subagent | `.agents/agents/implementer.md` | `.claude/agents/implementer.md`, pinned to Opus            | `.codex/agents/implementer.toml` (model)                    |
| `reviewer-opus`        | `.agents/agents/reviewer.md`    | `.claude/agents/reviewer-opus.md`, on Opus, read-only      | none: Codex uses `reviewer`                                 |

- **`AGENTS.md` is the only instructions file**, here and in every parent directory. Claude Code
  reads `AGENTS.md` only as a fallback, when no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md`
  sits in the working directory or above it, so adding one would silently stop it reading these
  instructions. Claude-only notes go in `~/.claude/CLAUDE.md`, which does not count.
- **Skills are the one symlink**: Claude Code reads skills only from `.claude/skills`, with no
  setting to add a directory, so `.claude/skills` points at `.agents/skills`. The symlink is tracked
  by git.
- **A new skill** goes in `.agents/skills/<name>/` and both harnesses see it; there is nothing to
  link.
- **A hook change** is a change to the script. Adding or removing a hook touches both wiring files,
  which carry the same events and matchers (Codex accepts `Write|Edit` for its `apply_patch` tool).
  The scripts read either payload: Claude Code's `tool_input.file_path` or a Codex patch in
  `tool_input.command`, and `$CLAUDE_PROJECT_DIR` or, when Codex leaves it unset, the checkout the
  hook runs in.
- **`implementer` runs on its harness's own model**: it edits, tests and commits in its own worktree.
  Claude Code's wrapper pins Opus in its frontmatter, since a subagent left to the user's default
  (`CLAUDE_CODE_SUBAGENT_MODEL`) may run on Haiku; Codex's names gpt-6.1-sol.
- **The review roles and research run on Codex models whichever harness orchestrates**: a Claude
  session in T3 reaches them through `delegate_task`, Codex through its own agents. Which model,
  effort and route each takes lives in one place: "Spawning a reviewer" in the `code-review` skill
  for the reviewers, [Delegating to subagents](#delegating-to-subagents) below for research. The
  `.toml` wrappers repeat the model for Codex, which reads it nowhere else.
- **The correctness axis runs on Opus** under Claude Code, through `reviewer-opus`, so the axis that
  hunts for bugs is a second model family beside the Codex axes. Codex cannot run Opus, so under
  Codex the axis is spawned as `reviewer`, on Sol like the rest.
- **Codex reads `.codex/` from the main checkout, even in a worktree**: a T3 worktree gets the hooks
  and the subagent wrappers only once they are on the branch the main checkout has out, while
  `AGENTS.md` and the skills come from the worktree itself. The hook commands resolve
  `git rev-parse --show-toplevel`, so the scripts that run are the worktree's.
- **Codex runs a project hook only once it is trusted**: the project must be trusted, and each hook
  reviewed and approved when Codex first offers it.
- **Harness-only files stay where they are**: the permission allowlist in `.claude/settings.json`
  has no Codex counterpart.

## Session hooks

Hooks are configuration, not a terminal feature, so they run in a headless session too. They read
JSON on stdin and need `jq`.

- **`SessionStart`**: `check-tool-path.sh` adds a warning to the session's context when its shell
  cannot find `uv`, `docker` or `gh`, pointing at [the agent shell's PATH](#the-agent-shells-path).
  It never edits PATH itself.
- **`PreToolUse` on Bash**: `block-pkill-f.sh` blocks `pkill -f` and `pkill --full`, whose pattern
  matches the shell running it and kills the agent's own Bash call (exit 144). The message names
  `uv run just dev-down`.
- **`PostToolUse` on `Write|Edit`**: `format-edited-file.sh` runs `ruff format` and
  `ruff check --fix --exit-zero` over each edited `.py` file, silently, so formatting is not a
  session's to remember.
- **`Stop`**: `stop-lint-check.sh` runs `pre-commit run --files` on the changed `.py`, `.xml`,
  `.csv`, `.po`, `.sh` and manifest files of the uncommitted working tree, and **blocks** with exit 2
  when one fails, putting the output in front of the agent. It does not run the Odoo tests: that is
  `uv run just gate`, which the agent runs before a commit is done.

`SKIP_STOP_CHECKS` set to any value is the local bypass (`SKIP_STOP_CHECKS=1 claude`, or `codex`,
or exported for the session). The gate keeps blocking while the failure persists; Claude Code
force-closes the turn after 8 consecutive blocks, so the wording of the last instruction is all
`stop_hook_active` decides.

## The agent shell's PATH

T3 Code, and the Claude Code and Codex sessions it starts, inherit PATH from the desktop login
session. That session reads `~/.profile`, not `~/.bashrc`, so a tool directory added only in
`~/.bashrc` is on PATH in a terminal and missing in an agent's shell. `uv` lives in `~/.local/bin`,
which is the line this machine needs in `~/.profile`:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

`docker` and `gh` are system binaries here. A change to `~/.profile` takes effect at the next login,
not in a running T3 Code.

When the `SessionStart` warning fires, the fix is that profile line, made by the user. A session
does not prefix its commands with `export PATH=…`: that hides the cause from the next session, which
then pays for it again.

## Delegating to subagents

A subagent costs a full orientation and returns only its summary, so delegate by the size of the
read, not the size of the task:

- Reading one to three files to decide or verify something is inline work.
- Understanding that needs four or more files is one narrow mapping subagent, which returns the
  conclusion, not the file dumps.
- Bulk output (a long diff, a log, a rendered page) is read by a subagent when only its conclusion
  is needed in the main thread.
- Bash for state (`git`, `gh`) stays inline.

Brief a subagent with the exact paths and skill files to read, never a digest of them, and ask for
its report as text with a fixed shape: status, one-line summary, artifacts touched, next step, risks.
A subagent whose last action is a tool call returns the tool result instead of its report.

Reading outside the repo goes to the `research` agent (`.agents/agents/research.md`), on Codex's
gpt-6-luna at medium effort: it judges and condenses sources more than it reasons, and Luna spares
the Sol quota. It fetches plain-text sources with `curl`, and searches and reads rendered pages with
its harness's web search. Spawn it the way the `code-review` skill's "Spawning a reviewer" spawns a
Codex role, with this model and effort and `role: "research"`, its task opening with "Before anything
else, read `.agents/agents/research.md` and follow it."; under Codex as the `research` agent; outside
T3, from Claude Code, as the `research` agent, which runs on Sonnet.
