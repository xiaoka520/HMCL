#!/usr/bin/env bash
# Merge upstream into a temporary checkout; publishing happens only after all builds pass.
set -euo pipefail

policy_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
region_path=HMCL/src/main/java/org/jackhuang/hmcl/util/RegionUtils.java

if [[ -n "$(git status --porcelain)" ]]; then
  echo 'Refusing to synchronize a dirty checkout.' >&2
  exit 1
fi

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git fetch --no-tags https://github.com/HMCL-dev/HMCL.git main
upstream_sha="$(git rev-parse FETCH_HEAD)"
if ! git merge --no-ff --no-commit "$upstream_sha"; then
  conflicts="$(git diff --name-only --diff-filter=U)"
  # Only the centrally maintained download policy may be resolved automatically.
  if [[ "$conflicts" != "$region_path" ]]; then
    echo 'Upstream merge needs manual resolution:' >&2
    echo "$conflicts" >&2
    exit 1
  fi
  git checkout --theirs -- "$region_path"
fi

python3 "$policy_dir/download_policy.py" --apply
python3 "$policy_dir/test_download_policy.py"
git add -- "$region_path"
if git rev-parse -q --verify MERGE_HEAD >/dev/null; then
  git commit -m "Merge HMCL upstream ${upstream_sha:0:12} with unrestricted downloads"
elif ! git diff --cached --quiet; then
  git commit -m 'Restore unrestricted download policy'
fi
git merge-base --is-ancestor "$upstream_sha" HEAD
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "upstream_sha=$upstream_sha" >> "$GITHUB_OUTPUT"
fi
