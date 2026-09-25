#!/usr/bin/env bash
# Clone each addons repo at a pinned branch into /mnt/extra-addons/<name>.
# Called from the Dockerfile. Format of repos.txt: <name> <git-url> <branch>
set -euo pipefail
target="${1:-/mnt/extra-addons}"
repos="${2:-repos.txt}"
mkdir -p "$target"
grep -vE '^\s*(#|$)' "$repos" | while read -r name url branch; do
  echo ">>> $name ($branch)"
  git clone --depth 1 --branch "$branch" "$url" "$target/$name"
  rm -rf "$target/$name/.git"
done
