"""Pick the instance a script talks to and load its env file into os.environ.

    --target local     (default) .env           → the dev copy on localhost
    --target deployed            .env.deployed  → the Coolify instance
Scripts that write data pass writes=True; against the deployed instance they then also need
--yes-deployed. The URL must agree with the target, so a misfilled file cannot cross over.
"""

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
FILES = {"local": ".env", "deployed": ".env.deployed"}
LOCAL_HOSTS = {"localhost", "127.0.0.1"}


def load(writes, argv=None):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--target", choices=sorted(FILES), default="local")
    p.add_argument("--yes-deployed", action="store_true")
    a, _ = p.parse_known_args(argv)
    f = ROOT / FILES[a.target]
    if not f.exists():
        sys.exit(
            f"{f.name} missing: cp .env.example {f.name}"
            + (" and fill in the deployed values" if a.target == "deployed" else "")
        )
    vals = dict(
        line.split("=", 1) for line in f.read_text().splitlines() if "=" in line and not line.lstrip().startswith("#")
    )
    os.environ.update(vals)  # the file wins over the shell: the target decides, nothing else
    host = urlparse(os.environ["ODOO_URL"]).hostname
    if (host in LOCAL_HOSTS) != (a.target == "local"):
        sys.exit(f"{f.name}: ODOO_URL host {host} does not match --target {a.target}")
    if writes and a.target == "deployed" and not a.yes_deployed:
        sys.exit("refusing to write to the deployed instance without --yes-deployed")
    print(f":: target {a.target} ({os.environ['ODOO_URL']}, db {os.environ['ODOO_DB']})")
    return a.target
