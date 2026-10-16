# Research sources

What the shared `research` agent prefers for this stack: Odoo 19 with the ADHOC Argentine
localization.

## Pinned versions

- Odoo and every addons repo (ADHOC, OCA): `prototype/repos.txt`, one commit per repo. Read the
  source at that commit, not at the branch head.
- The Odoo image: `prototype/Dockerfile` (`odoo:19.0`, by digest).
- Python tooling and the image's pip packages: `pyproject.toml` with `uv.lock`, and
  `prototype/requirements.txt`.

## Primary sources

- Odoo's own source and docs. The documentation is reStructuredText in the `odoo/documentation`
  repo, so fetch the raw file with `curl` rather than the rendered page.
- The ADHOC and OCA repositories, at the commit `repos.txt` pins.
- ARCA's official documentation of its webservices (WSFE, the CAE request), for anything fiscal.
- PyPI's JSON API for a Python package.

Odoo's source at the pinned commit counts as code, not docs: when it and a doc disagree, the source
is what runs. A finding a later decision will cite goes in `docs/research/<kebab-name>.md`, as
[issue-tracker.md](issue-tracker.md#research-tickets) says.
