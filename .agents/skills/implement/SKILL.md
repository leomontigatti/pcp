---
name: implement
description: "Implementation workflow: explore, test-first at agreed seams, validate, review, commit. Use when asked to build a feature, fix a bug, or change code in a local session."
---

<!--
  Started as the `do-work` skill vendored from mattpocock/course-video-manager; reshaped after
  `implement` in mattpocock/skills, then reshaped for Odoo: the browser step is a scenario or a
  shell snippet, and the DB TDD notes are `ODOO-TDD.md`. This is the only implementation workflow.
-->

# Implement

## 1. Explore

Start current: `git fetch origin && git log --oneline HEAD..origin/main` prints nothing, or you
merge `origin/main` in first
([workflows.md](../../../docs/agents/workflows.md#branches-worktrees-and-t3-code-threads)).

Read the issue or request, then `CONTEXT.md`, the ADRs under `docs/adr/` that touch the area, the
addon's manifest (`prototype/addons/<module>/__manifest__.py`) and the tests beside the code you
will change. Done when you can name the **seams**: the public interfaces the behaviour will be
tested through. In Odoo that is usually a model method, called through the ORM, or a controller
route.

Take the seams from the ticket's **Test seams** when it has them. Otherwise propose them and
confirm with the user; in an unattended run, choose them and state them in the commit body. When
where a seam belongs is itself the question, call the Skill tool with "codebase-design". When the
change renames a domain term or edits `CONTEXT.md` or an ADR, call it with "domain-modeling".

If the change alters what a user sees (a view, a report, a printed document), write down how it
looks now, before the first edit, so the report can compare.

## 2. Build test-first

Call the Skill tool with "tdd" and follow its loop at those seams: one failing test, the minimal
code to pass it, repeat.

- Code that touches models, the ORM or the database: also follow [ODOO-TDD.md](ODOO-TDD.md).

Validate as you go: `uv run just test <module>` each time a slice goes green, narrowed with
`TEST_TAGS='/<module>:<Class>.<test>'` while you iterate (see
[validation.md](../../../docs/agents/validation.md)).

## 3. Validate once at the end

Run `uv run just gate` (every linter, then the tests of every addon, failures only). Lint may
auto-fix files: rerun until it passes. Fix and re-run until it is clean before moving on.

## 4. Verify what a user sees

When the change alters a view, a report, a printed document or a wizard, drive the flow against
the local copy: a scenario from `uv run just scenarios` when one covers it, or a snippet through
`echo '<code>' | uv run just dev-shell`. Pcp has no browser or screenshot tooling yet, so do not
claim a screen works from the tests alone: name in the final report the screens nobody looked at,
and attach the before and after text or output instead of images. Skip this step for changes with
no rendered surface, and say so.

## 5. Review

Spawn every reviewer the way "Spawning a reviewer" in the `code-review` skill says: the model
each axis runs on, and how this harness reaches it.

Tier the review by risk:

- **Full review** when the diff touches money (prices, invoicing, IVA, CAE, comprobantes,
  payments), auth or access rules, a migration or module upgrade, a term defined in `CONTEXT.md`,
  or an operational script that deletes or overwrites (`prototype/scripts/`, `dev-pull`, a
  database reset or restore): call the Skill tool with "code-review" on the changes since the
  branch point, and add the correctness axis. The reviewer starts from its prompt alone, so paste
  the spec's body and comments into the Spec axis's prompt, never a `gh` command for it to run.
- **Readback** for everything else: follow [READBACK.md](../code-review/READBACK.md). One sub-agent
  restates what the diff does and flags anything surprising, in under 200 words. When the diff
  changes behaviour, add the correctness axis beside it, config included (a security group, a
  report template, a server setting). A docs-only diff, or a config-only one that changes no
  runtime behaviour (tooling, agent or editor settings), keeps the readback alone.

The correctness axis is [CORRECTNESS.md](../code-review/CORRECTNESS.md): one sub-agent, on Opus,
that assumes the diff has a bug and traces the path that triggers it. It runs in the same message
as the other review spawns.

A finding is a claim to check, never an instruction. Verify each one against the code on the
branch, running the test or the call when reading does not settle it, then give it one verb:

- **fix**: the claim holds and the change is in scope.
- **decline**: the code disproves it. Keep the disproof (a `file:line`, a test, the invariant
  that covers it) for the final report.
- **ask**: the call is the user's, which includes every finding that touches the always-ask list
  below that you cannot settle from the issue. Bring it to them in the final report.

Always **ask** when the finding touches money (prices, invoicing, IVA, CAE, comprobante emission),
results of a fiscal submission, auth or access rules, a migration, a destructive data path, or a
term defined in `CONTEXT.md`; when it needs a product decision; and when a person, not a reviewer,
opened the thread.

When the spec and a standard in `AGENTS.md` or `docs/agents/` disagree, the standard wins unless
the spec names the exception in so many words: a spec that points at a nonconforming module as its
model asks for the module's shape, not its breach. Such a finding is a Standards one whichever
axis raised it, and it is a **fix**, or an **ask** when an exception is wanted. A finding backed by
the standards is never a **decline** on your judgement alone.

Then walk the **breadth** list and say in the final report which entries applied: the common
defect is a change that works on the tested path and is missing everywhere else.

- **Reverse states.** A way in needs its way out and a way to see it: confirm needs cancel, post
  needs a visible posted state and, where the domain allows it, reset to draft. A transition the
  domain makes irreversible (an invoice number that is assigned, a CAE that was granted) shows its
  terminal state and says so.
- **Entry points.** A behaviour reachable from a form is usually reachable from the list view, the
  report, the API, a wizard or a cron. Name the paths you checked and the ones deliberately
  different.
- **Docs.** Whether the change makes existing guidance wrong, by the
  [documentation rules](../../../docs/agents/workflows.md#documentation).

Done when every finding carries a verb, every **fix** is made and the breadth list is walked.
Repeat step 3 for anything you touched. Refactoring belongs here, under green tests.

## 6. Commit

Commit to the current branch when the run started from an issue, the user asked for a commit or a
PR, or the run is unattended; otherwise report the result and leave the tree for the user. An
explicit request from the user not to commit overrides all of these. Conventional-commit subject
and body in English; the subject names the module when one module owns the change.

## 7. Open the PR and hand it off

When the run started from an issue or the user asked for a PR: push the branch, open it ready for
review (never a draft; a PRD run under `implement-spec` keeps its PR a draft until the last slice
lands) with a body written by calling the Skill tool with "pr", carrying `Closes #N`, attach the
step 4 evidence when step 4 produced any, and link it to the thread. An issue is the unit of work
here, so a run that starts from one ends in the PR that closes it unless the user says otherwise.
Done when `gh pr view` shows it open and it is linked.

Then call the Skill tool with "babysit-pr": this session judges the review rounds, and the waiting
is done by a background watch, so the session wakes only when a round needs it. Stop only at the
skill's report.
