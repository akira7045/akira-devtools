#!/usr/bin/env bash
# publish.sh — push all four dev-tool repos to GitHub in one shot.
#
# Usage:
#   GH_TOKEN=ghp_xxx GH_USER=yourname ./publish.sh
#   # or, if repos already exist and remotes are set:
#   GH_TOKEN=ghp_xxx ./publish.sh
#
# Requires: git, curl. Creates the repos via the GitHub API if they don't
# exist, then pushes. Idempotent: safe to re-run.
set -euo pipefail

: "${GH_TOKEN:?set GH_TOKEN (Personal Access Token with repo scope)}"
: "${GH_USER:?set GH_USER (your GitHub username)}"

API="https://api.github.com"
DIR="$(cd "$(dirname "$0")" && pwd)"
REPOS=(secretscan apidiff jsonl2csv dupfind)
DESCS=(
  "Zero-dependency secret scanner: single-file, stdlib-only, pre-commit ready."
  "Zero-dependency API response differ: snapshot & detect contract drift."
  "Zero-dependency JSON/JSONL to CSV converter with data-quality checks."
  "Zero-dependency duplicate file finder by hash. Read-only by design."
)

api() { curl -sS -H "Authorization: token $GH_TOKEN" -H "Accept: application/vnd.github+json" "$@"; }

for i in "${!REPOS[@]}"; do
  repo="${REPOS[$i]}"
  desc="${DESCS[$i]}"
  src="$DIR/$repo"
  echo "==> $repo"

  # Create the repo if it doesn't exist yet (404 => create).
  state=$(api -o /dev/null -w "%{http_code}" "$API/repos/$GH_USER/$repo")
  if [ "$state" = "404" ]; then
    echo "    creating $GH_USER/$repo ..."
    api -X POST "$API/user/repos" \
      -d "{\"name\":\"$repo\",\"description\":\"$desc\",\"private\":false,\"has_issues\":true}" \
      -o /dev/null -w "    status:%{http_code}\n"
  else
    echo "    repo exists (status:$state)"
  fi

  # Set remote and push.
  if git -C "$src" remote get-url origin >/dev/null 2>&1; then
    git -C "$src" remote set-url origin "https://$GH_USER:$GH_TOKEN@github.com/$GH_USER/$repo.git"
  else
    git -C "$src" remote add origin "https://$GH_USER:$GH_TOKEN@github.com/$GH_USER/$repo.git"
  fi
  git -C "$src" push -u origin HEAD:main 2>&1 | tail -1
done

echo "==> done. Visit https://github.com/$GH_USER"
