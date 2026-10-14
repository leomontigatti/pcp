# Triage Labels

The list of labels — name, colour, description — is [`.github/labels.json`](../../.github/labels.json).
That file says what they mean. Add or change a label in the JSON, run `uv run just labels-sync`, then
describe it here.

The skills speak in terms of five canonical triage roles. Three map to a label here; the other two map to what replaced them:

| Label in mattpocock/skills | Label in our tracker           | Meaning                                                                                                 |
| -------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------- |
| `needs-triage`             | `needs-triage`                 | Maintainer needs to evaluate this issue                                                                 |
| `needs-info`               | `question` + `ready-for-human` | Not specified enough to act on; a person has to decide first                                            |
| `ready-for-agent`          | `ready-for-agent`              | Fully specified & grabbable — triage state, **not** an AFK trigger                                      |
| `ready-for-human`          | `ready-for-human`              | Needs a human: a decision to settle or work an agent cannot do                                          |
| `wontfix`                  | none: close it                 | Close `not planned` with a `Closure:` comment ([issue-tracker.md](./issue-tracker.md#closing-an-issue)) |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

`needs-info` and `wontfix` were retired. With one maintainer there is no reporter to wait on, so "needs more
information" is a decision the maintainer owes, which is what `question` + `ready-for-human` already say. And a
decision not to do something is made by closing: an open issue labelled "will not be actioned" is a closure
that did not happen.

## Priority and type

The roles above say whether an issue can be picked up. They do not say how much it matters. Triage also gives
every issue exactly one priority label and at least one type label, and removes `needs-triage` on the way out.
An issue with no `priority:*` label has not been triaged.

| Priority label    | Meaning                                                                                  | Test                                   |
| ----------------- | ---------------------------------------------------------------------------------------- | -------------------------------------- |
| `priority:urgent` | Breaks invoicing, money or stock, or the next go-live cannot run without it              | Would I drop what I am doing for this? |
| `priority:next`   | The short list to pull from next. Keep it to about 15                                    | Will I start this within two weeks?    |
| `priority:later`  | Worth doing, no blocker, not scheduled                                                   | Would I be sad to close it?            |
| `priority:parked` | Deliberately not now, and the issue names what wakes it                                  | Is there a condition that reopens it?  |

`priority:urgent` is empty outside the run-up to a go-live. Dated work also goes in a milestone ("Before
go-live"), which is what carries the deadline; the label only says it comes first. A parked issue carries a
comment stating its wake-up trigger ("the ARCA homologation passes"); without one it is `priority:later`.
Deciding against is a different thing: parked will be done when the trigger fires, a rejected issue is closed.

| Type label    | Meaning                                                                   |
| ------------- | ------------------------------------------------------------------------- |
| `bug`         | Wrong behaviour today                                                     |
| `enhancement` | New capability or UX                                                      |
| `refactor`    | Internal structure, no behaviour change                                   |
| `chore`       | Dependencies, tooling, CI, docs or operations                             |
| `question`    | A decision to settle rather than work to do; pairs with `ready-for-human` |

The dispatch queue is `priority:next` plus `ready-for-agent`:
`gh issue list --label priority:next --label ready-for-agent`. Skip an issue whose
`gh issue view <n> --json blockedBy` still lists an open blocker: blocking is GitHub's native relation
([issue-tracker.md](./issue-tracker.md#ticket-operations)), and no label tracks it.

Sub-issues are not triaged on their own. `to-tickets` creates each slice with its PRD's priority, type and
milestone. That multiplies a PRD in any priority list, so add `no:parent-issue` for the PRD-level view:
`gh issue list --label priority:next --search "no:parent-issue"`.

> **`ready-for-agent` triggers nothing.** It is a triage state ("specified and grabbable"): a local session
> picks the issue up from the dispatch queue above. No label starts a run.
