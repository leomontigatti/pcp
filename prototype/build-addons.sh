#!/usr/bin/env bash
# Fetch each addons repo at its pinned commit into /opt/odoo-addons/<name>.
# Called from the Dockerfile. Format of repos.txt: <name> <git-url> <branch> <commit>
set -euo pipefail
target="${1:-/opt/odoo-addons}"
repos="${2:-repos.txt}"
mkdir -p "$target"
grep -vE '^\s*(#|$)' "$repos" | while read -r name url branch commit; do
  echo ">>> $name ($branch @ ${commit:0:12})"
  git init -q "$target/$name"
  git -C "$target/$name" fetch -q --depth 1 "$url" "$commit"
  git -C "$target/$name" checkout -q FETCH_HEAD
  rm -rf "$target/$name/.git"
done
