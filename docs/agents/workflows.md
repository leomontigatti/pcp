# Workflows

How work flows in a local session here: where it starts, what this repo's worktrees need, when to
investigate before recommending, and when a change needs a doc change. The rules for branches,
worktrees, threads and PRs every session follows are the shared `implement` skill's `THREADS.md`;
how a change to what a user sees is checked is [verification.md](./verification.md).

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
the same session, with the waiting done by T3's `watch_pull_request` (the `babysit-pr` skill).

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

## This repo's worktrees

`t3.json`'s `runOnWorktreeCreate` script links `prototype/.env` from the main checkout and runs
`uv sync --locked` before the agent starts. In the main checkout, where T3 also runs it for a thread
with no worktree, it leaves `prototype/.env` alone and only syncs. A worktree with no
`prototype/.env` link means the script never ran: the fix is importing `t3.json` (project settings
→ Actions → Import from t3.json), then running the script's command by hand for that worktree.

The machine runs one Postgres and one Odoo image for every worktree: the shared rule that services
run once per machine belong to the orchestrator's checkout holds for them, and any worktree's
recipe starts Postgres when it is down. What is per worktree is the Odoo that checks a screen: its
own copy of `proto`, served from its own `prototype/addons` on its own port, started with
`dev-up` only while the worktree checks a screen ([verification.md](./verification.md#launch)), so
an `implement-spec` implementer starts its own in its worktree. Each test run clones the template
into a throwaway database of its own. A deleted worktree leaves its database and
filestore behind until the `housekeeping` sweep ([housekeeping.md](./housekeeping.md)).

## Documentation

Most code changes need no documentation change: agents and maintainers read the code. Before adding a
paragraph anywhere under `docs/`, ask what a maintainer or a later session would get wrong without
it. If reading the relevant code answers the question, leave it out.

- `docs/agents/` holds operative rules and the traps that are hard to discover from the source.
  `GLOSSARY.md` holds the vocabulary, and `docs/adr/` holds decisions and their reasons.
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
