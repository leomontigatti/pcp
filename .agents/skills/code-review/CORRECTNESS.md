<!--
  The brief follows the reviewer prompt and rubric of `interrogate` in cursor/plugins
  (pstack/skills/interrogate), cut to one model.
-->

# Correctness

The bug-hunting axis of step 5 of the `implement` skill. It runs on every diff that changes
behaviour: beside the readback, or as the third axis of the full review. Standards asks whether
the code follows the repo's conventions and Spec whether it does what the issue asked; this one
asks whether it is **wrong**. The areas the brief names are where this codebase has been hurt before.

1. Use the fixed point, diff command and commit list pinned for `code-review`, or for the
   readback.
2. Spawn **one** `reviewer-opus` sub-agent, in the same message as the other review spawns, with
   the diff command, the commit list, one paragraph stating what the change is meant to do, and
   the brief below. It runs on Opus while the other axes run on Codex models, so the axis that
   hunts for bugs brings a second model family. Codex has no Opus agent: under Codex, spawn
   `reviewer`.

   > Assume this diff has a bug its author's tests miss, and hunt for it. The stated intent is
   > correct; challenge the execution. Read the callers and callees of every changed function,
   > beyond the diff. Look where this codebase gets hurt: amounts that round, split or sum to
   > something other than the total, a comprobante whose number, CAE or IVA breakdown disagrees with its total; a controller, route or model method reachable by a user who should be
   > refused (record rules, groups, `sudo()`); an action that runs twice, or stops halfway; a migration or module upgrade the
   > previous container runs against during the deploy; empty, zero, null and boundary values; an error caught and
   > dropped; a guard that hides a broken invariant where the invariant should be fixed; a rule
   > the client and the server each enforce, in two copies that disagree; a second write path
   > (another method, controller, onchange or cron reaching the same record) missing the access or
   > validation check the first one has; state that goes stale after a save or a navigation, a
   > dialog or an onchange that outlives what it belongs to; an HTTP header, cookie or cache directive that
   > leaks, caches or blocks what it should not; a script that deletes or overwrites (an
   > `rsync --delete`, a reset, a restore) pointed at the wrong target or run with an empty
   > variable.
   >
   > For each finding give its severity (`critical`: a wrong result, lost or corrupt data, a
   > security hole; `warning`: holds today and breaks under a condition you can name), the hunk
   > (file and line), and the **path** that triggers it: the input or sequence of calls, traced
   > through the code, that makes it go wrong. A suspicion you could not trace to a path goes
   > under "Untraced", one line each. Style, naming and structure belong to another reviewer.
   >
   > End with one line: `Would merge: yes | after fixes | no`, and the finding that decides it.
   > "No findings" is a valid review. Under 400 words.

3. Report it under `## Correctness`, after `## Standards` and `## Spec` or after `## Readback`,
   verbatim or lightly cleaned, and add its count and worst finding to the closing summary line.
