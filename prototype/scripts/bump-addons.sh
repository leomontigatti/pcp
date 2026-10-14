#!/usr/bin/env bash
# Move pins in repos.txt to the current head of each repo's branch.
#   scripts/bump-addons.sh            all repos
#   scripts/bump-addons.sh <name>...  only these
# Prints one line per repo: unchanged, or old..new with a compare URL to review.
set -euo pipefail
cd "$(dirname "$0")/.."
only=" $* "
tmp=$(mktemp)
while IFS= read -r line; do
  if [[ "$line" =~ ^[[:space:]]*(#|$) ]]; then echo "$line"; continue; fi
  read -r name url branch commit <<<"$line"
  if [[ -n "${*}" && "$only" != *" $name "* ]]; then echo "$line"; continue; fi
  head=$(git ls-remote "$url" "refs/heads/$branch" | cut -f1)
  [[ -n "$head" ]] || { echo "error: $name: branch $branch not found" >&2; exit 1; }
  if [[ "$head" == "$commit" ]]; then
    echo "$name unchanged" >&2
  else
    echo "$name ${commit:0:12}..${head:0:12} ${url%.git}/compare/$commit...$head" >&2
  fi
  echo "${line/$commit/$head}"
done < repos.txt > "$tmp"
mv "$tmp" repos.txt
