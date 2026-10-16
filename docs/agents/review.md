# Review

What the shared review (`implement` step 5, `code-review`, `pr`) needs to know about this repo:
where a diff is risky, which findings are the user's call, and where the code has been hurt.

## Full review

A diff that touches any of these gets the full review (Standards, Spec and correctness):

- **Money**: prices and price lists, discounts, invoicing, IVA and the other taxes, CAE and
  comprobante numbering, Perceptions and Withholdings, payments.
- **Access**: security groups, record rules, `ir.model.access.csv`, `sudo()`.
- **Migrations and module upgrades**: a module's `migrations/`, a version bump in its
  `__manifest__.py`, the addon pins in `prototype/repos.txt` (they move the ADHOC and OCA code
  every invoice runs through), and the upgrade on start in `prototype/entrypoint.sh`.
- **Reaching ARCA or the deployed instance**: the targeting in `prototype/lib/` (`--target
  deployed`, `--yes-deployed`), `setup-proto.py` and `scenarios.py`, which write wherever that
  targeting points, the neutralization of the local copy in `prototype/entrypoint.sh`, and the
  deploy itself (`prototype/docker-compose.yaml`, `Dockerfile`, `config/`).
- **Scripts that delete or overwrite**: `prototype/dev-pull.sh`, `prototype/init-db.sh`,
  `prototype/scripts/`.

The `review-paths` block is the same list as paths, for `review.py tier`. Paths under
`prototype/addons/` match by name, so a module is full when its name or a file in it names the
area; raise the tier by hand for a module whose name does not.

```review-paths
full money: ^prototype/addons/.*(pric|discount|invoic|account|tax|iva|cae|comprobante|fiscal|percep|withhold|payment|l10n_ar)
full access: ^prototype/addons/.*(/security/|ir\.model\.access\.csv$|_rules?\.xml$|groups?\.xml$)
full migration: ^prototype/addons/[^/]+/(migrations/|__manifest__\.py$)
full upgrade: ^prototype/(repos\.txt|entrypoint\.sh|build-addons\.sh)$
full deployed: ^prototype/(lib/|setup-proto\.py$|scenarios\.py$|docker-compose\.yaml$|Dockerfile$|config/)
full destructive: ^prototype/(dev-pull\.sh|init-db\.sh|scripts/)
quiet: ^\.pre-commit-config\.yaml$
quiet: ^\.shellcheckrc$
quiet: ^\.gitignore$
quiet: ^\.github/dependabot\.yml$
```

## Always ask

A finding in one of these that the issue does not settle is the user's call:

- Money: prices, invoicing, IVA, CAE, comprobante emission, and the result of any fiscal
  submission.
- Auth and access rules.
- A migration or module upgrade, and a merge conflict inside one or inside an access rule.
- A destructive data path, and anything that writes to the deployed instance.
- A term defined in `GLOSSARY.md`.

## Hotspots

Where this codebase gets hurt, for the correctness brief:

- Amounts that round, split or sum to something other than the total; a comprobante whose number,
  CAE or IVA breakdown disagrees with its total.
- A controller, route or model method reachable by a user who should be refused (record rules,
  groups, `sudo()`); a second write path (another method, controller, onchange or cron reaching
  the same record) missing the check the first one has.
- An action that runs twice, or stops halfway: a confirm, a post, a CAE request.
- A migration or module upgrade the previous container runs against during the deploy;
  `click-odoo-update` upgrades changed modules on start, and a failed upgrade stops the container.
- An onchange or a dialog that outlives the record it belongs to.
- The local copy reaching ARCA: `odoo neutralize` and the ARCA URL rewrite in
  `prototype/entrypoint.sh` must run after every upgrade, since `-u` reloads module data.
- A script that deletes or overwrites (`dev-pull`, a reset, a restore) pointed at the wrong target
  or run with an empty variable; a write that reaches the deployed instance without
  `--yes-deployed`.

## Breadth

- **Reverse states, in Odoo**: confirm needs cancel, post needs a visible posted state and, where
  the domain allows it, reset to draft. An invoice number that is assigned, or a CAE that was
  granted, is irreversible: the record shows that terminal state and says so.
- **Entry points, in Odoo**: a behaviour reachable from a form is usually reachable from the list
  view, a report, the API (XML-RPC, as `scenarios.py` uses it), a wizard, a cron and the Point of
  Sale. Name the ones checked and the ones deliberately different.
- **Docs**: by the rules in [workflows.md](workflows.md#documentation).

## One-way doors

- A module upgrade or migration that drops or rewrites data, or that the previous container cannot
  run against during the deploy.
- Anything sent to ARCA: an invoice, a CAE request. A comprobante with a CAE cannot be unsent.
- Writes to prices, invoicing or comprobantes that reach the deployed instance, and any change to
  how an existing comprobante reads.
- An email sent to a customer.
- Production: the deployed instance, its Coolify resource, DNS, secrets, the storage volume.
- Deleting data anywhere outside the local dev database.
