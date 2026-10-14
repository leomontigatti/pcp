# Workflows

How work flows in a local session: where it starts, which checkout it happens in, when to
investigate instead of editing, when it needs a doc change, and how a change to what a user sees is
checked.

## Where work starts

Implementation happens in a local T3 Code session. Three entry points, by how much is still unknown:

- **Small and clear** (a bug, a one-module change): say it in the thread, or write the issue with
  what to build and its acceptance criteria and label it `ready-for-agent`. No PRD, no map. A session
  grabs it and runs the `implement` skill.
- **Clear but big** (known shape, several slices): `/grilling` until the shape and the test seams are
  agreed, `/to-spec` to file the PRD ([PRD workflow](./issue-tracker.md#prd-workflow)), `/to-tickets`
  to slice it into sub-issues ([Ticket operations](./issue-tracker.md#ticket-operations)), then
  `/implement-spec <PRD>`. The session runs every unblocked sub-issue at once in `implementer`
  subagents, merges each onto its branch and one draft PR, ticking each in the PR body's
  `## Sub-issues` list as it lands ([pull-requests.md](./pull-requests.md#prd-prs)), and reviews and
  babysits the chain once at the end: a resumed session reads the list, never the scrollback.
- **Foggy** (decisions nobody has made yet): `/wayfinder`. The map's tickets are grilling, research,
  prototype or task; a prototype is a throwaway artifact whose result is a decision on its ticket,
  never another PRD. The map ends with one or more PRDs, per the exit shapes in
  [issue-tracker.md](./issue-tracker.md#wayfinding-operations).

A request in the thread names the finish line and the allowed stops, so the session knows when it is
done and when to ask:

```
Implement #1234, open the PR and babysit it.
Done means: the acceptance criteria pass, a regression test cites the issue, and the PR is ready
to merge. Stop only if the seams are unclear.
```

The PR is reviewed in the session before it is opened (`implement` step 5) and babysat afterwards by
the same session, with the waiting done by T3's `watch_pull_request` (`babysit-pr`, per
[pull-requests.md](./pull-requests.md#babysitting-a-pr)).

## Investigate before implementing

A request to investigate, review, diagnose, audit, analyze or explain is a request for findings:
return them with the relevant context, the options and their tradeoffs, and a recommended next step,
then wait. Editing starts when the user asks to implement, fix, apply or make the change.

## Investigate before recommending

Put a recommendation to the user only once the option you are ruling _out_ has been researched as
thoroughly as the one you are arguing _for_.

- **A recommendation that discards an option is a claim about that option.** Searching only the
  favoured branch and then re-searching when the recommendation is contested produces confident
  claims that get reversed a turn later.
- **Mark every claim as verified or inferred.** A statement about how the system behaves needs a
  `file:line` behind it. If there is none, say so explicitly instead of stating it flatly.
- **The docs are not evidence about the code.** They can be stale or contradict what is implemented;
  when a doc and the code disagree, the code is what the system does. Check both before building an
  argument on either, and report the divergence. Odoo's own source (in the pinned commits of
  `prototype/repos.txt`) counts as code, not docs.
- **An architecture proposal** starts from the open architecture issues, so it duplicates none, and
  names one high-leverage change in the `codebase-design` skill's vocabulary rather than a list of
  cosmetic refactors.

## Branches, worktrees and T3 Code threads

Local sessions run inside [T3 Code](https://github.com/pingdotgg/t3code). Every T3 thread gets its own
git worktree and branch: `t3.json` at the repo root sets `defaultThreadEnvMode` to `worktree`, and its
`runOnWorktreeCreate` script links `prototype/.env` from the main checkout and runs `uv sync --locked`
before the agent starts. T3 runs that script only once it is imported (project settings → Actions →
Import from t3.json), once per T3 install; a worktree with no `prototype/.env` link means it never ran,
and the fix is the import, then the script's command by hand for that worktree. The local Odoo stack is one stack for
the machine, started with `uv run just dev-up` from any worktree; its database is the one every
worktree sees. The main checkout stays on `main` and is nobody's working directory.

Rules for a session:

- **Start current.** A thread can be older than the rules it builds against, and a worktree behind
  `main` reproduces what `main` already replaced. Before the first edit of an implementation,
  `git fetch origin && git log --oneline HEAD..origin/main` prints nothing; when it lists commits,
  `git merge origin/main` first.
- **Work where you started.** The thread's worktree is the working directory. Never `git checkout` or
  `git switch` in the main checkout, and never create a worktree of your own (`git worktree add`,
  Claude's `EnterWorktree`): T3 only tracks the branch and pull request of the worktree it created, so
  a private worktree loses the PR badge and the automatic settling of the thread. The one exception is
  `implement-spec`'s implementer subagents, each in an Agent-tool worktree under `.claude/worktrees/`:
  their branches merge into the thread's, which keeps the PR, and the skill removes them.
- **Branch prefixes.** T3 names the worktree's branch when it creates the thread and renames it once
  the thread starts, so read it with `git branch --show-current`, never from the worktree's folder
  name. A session that renames it or creates one uses `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`,
  `research/` or `prototype/`.
- **One thread, one branch, one PR.** After `gh pr create`, register the PR with the thread through
  the `link_pull_request` tool so T3 shows its status and settles the thread when it merges. To keep
  working on an existing PR, start the thread on that branch (or link the PR) instead of checking it
  out in another worktree. The PR body is written with the `pr` skill; how evidence is attached is in
  [pull-requests.md](./pull-requests.md).
- **Read-only threads** (writing issues, triage, reviewing a PR without editing code) must not change
  branches.
- **Leaving a worktree behind is fine; abandoning a branch is not.** Push the branch or delete it.
  T3's storage cleanup removes a thread's worktree once its PR merges or the thread is deleted, and
  keeps the branch; the branches, and the worktrees it skips, go with the `housekeeping` skill.

## Documentation

Most code changes need no documentation change: agents and maintainers read the code. Before adding a
paragraph anywhere under `docs/`, ask what a maintainer or a later session would get wrong without
it. If reading the relevant code answers the question, leave it out.

- `docs/agents/` holds operative rules and the traps that are hard to discover from the source.
  `CONTEXT.md` holds the vocabulary, and `docs/adr/` holds decisions and their reasons.
- Do not enumerate fields or methods, narrate control flow, keep file catalogs, or append PR
  summaries. Code, manifests and tests already record the implementation. A local explanation goes in
  a nearby code comment; a doc page is for reasoning that crosses boundaries.
- When a documented decision or constraint changes, rewrite or remove the affected text. Do not
  append a second account of the new behaviour. ADRs are the exception: they are records, so a change
  is a dated amendment section, and a reversal is a new ADR that supersedes.
- A session's plan, research notes and scratch files stay out of the repo. The issue and the PR are
  the record of the work. Only a plan that has to outlive its session is committed, as
  `docs/plans/<kebab-name>.md`, and is deleted when its work lands. Research that is a durable primary
  source goes under `docs/research/` per [issue-tracker.md](./issue-tracker.md#research-tickets).

## What a user sees

A change to a view, a report, a printed document or a wizard is checked against the local copy before
it is reviewed. Pcp has no browser or screenshot tooling yet, so the check is:

1. **Data:** `uv run just scenarios` runs the acceptance flows against the local database; for other
   data, `uv run just setup-proto` configures the instance. Never load data from the deployed
   instance: it carries the real CUIT, the ARCA certificate and CAE-backed invoices. `uv run just dev-pull` is the one exception,
   and it neutralizes the copy.
2. **Drive the flow** through the same path a user takes, or through `echo '<code>' | uv run just
   dev-shell` when the flow is a model method. Read the result back: the document text, the record's
   state, the printed output.
3. **Diagnose from the output, not from guesses:** `uv run just dev-logs` shows Odoo's log.
4. **Say what was not seen.** The final report names each screen nobody looked at with a person's
   eyes, so the reviewer knows which part rests on the tests alone.

Skip this for changes with no rendered surface, and say so. Never ask the user to check a screen by
hand: drive it and show the result.
