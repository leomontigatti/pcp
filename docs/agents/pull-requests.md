# Pull requests

How a PR is written here. The title is a Conventional Commit subject, since the squash merge makes it
the commit on `main`; nothing checks it yet. Branches and linking the PR to its T3 thread are in
[workflows.md](./workflows.md#branches-worktrees-and-t3-code-threads).

## Title and body

The title is a Conventional Commit (`feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, `test:`), with the
module in the scope when one module owns the change (`fix(pcp_pricing): ...`).

The body is written with the `pr` skill ([`.agents/skills/pr/SKILL.md`](../../.agents/skills/pr/SKILL.md)):
the template (Summary, Evidence, Merge Danger, `Closes #N`), the rules and the one-way doors of this repo
all live there. `.github/pull_request_template.md` is the same template for a PR opened by hand.

### PRD PRs

One PR carries every sub-issue of a PRD, with the body the `pr` skill describes. It is the one PR
opened as a **draft**: the `implement-spec` skill opens it after the first slice merges and marks it
ready when the last has landed and the chain has been reviewed, then babysits it. The chain pays one
review instead of one per slice.

## Evidence

A PR that changes what a user sees carries the before and after as text: the test that failed without
the change, or the printed document or the record state before and after, taken against the local copy
(see [workflows.md](./workflows.md#what-a-user-sees)). Pcp has no image upload yet, so a screenshot is
attached by hand when a reviewer needs one, and the PR says so.

- Never take evidence from the deployed instance: its documents carry the real CUIT and CAE-backed
  invoices.
- Never commit PR-only evidence to the repo.
- Say what was checked by hand and what was not. A list of green commands is a claim, not evidence.

## Babysitting a PR

Seeing a PR through CI and review is the `babysit-pr` skill: the session that opened the PR waits on a
background `gh pr checks <n> --watch`, wakes when a round needs judgement, fixes the findings that hold,
answers the rest with the reason, and stops at ready to merge. The merge stays the user's.

Branch protection requires a branch up to date with `main`, and nothing updates it on its own: the
babysit does it once, when being behind is all that is left (`gh pr update-branch`, or a local merge
when it conflicts). A PR nobody is babysitting is updated the same way by hand.

There is no automatic PR reviewer in this repo. The in-session review carries that job: the correctness
axis of `implement` step 5 runs on every diff that changes behaviour, on Opus beside the Codex axes.
