#!/usr/bin/env bash
# Merge upstream into a temporary checkout; publishing happens only after all builds pass.
set -euo pipefail

policy_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
region_path=HMCL/src/main/java/org/jackhuang/hmcl/util/RegionUtils.java
workflow_path=.github/workflows/fork-sync-build.yml

if [[ -n "$(git status --porcelain)" ]]; then
  echo 'Refusing to synchronize a dirty checkout.' >&2
  exit 1
fi

workflow_snapshot="$(mktemp)"
trap 'rm -f -- "$workflow_snapshot"' EXIT
cp -- "$workflow_path" "$workflow_snapshot"

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git fetch --no-tags https://github.com/HMCL-dev/HMCL.git main
upstream_sha="$(git rev-parse FETCH_HEAD)"
if ! git merge --no-ff --no-commit "$upstream_sha"; then
  unresolved=()
  # Reapply the fork's owned region/CI policies; leave other conflicts for review.
  while IFS= read -r -d '' conflict_path; do
    case "$conflict_path" in
      "$region_path")
        git checkout --theirs -- "$region_path"
        ;;
      .github/workflows/*.yml|.github/workflows/*.yaml)
        if [[ "$conflict_path" == "$workflow_path" ]]; then
          cp -- "$workflow_snapshot" "$workflow_path"
          git add -- "$workflow_path"
        else
          git rm --force -- "$conflict_path"
        fi
        ;;
      *) unresolved+=("$conflict_path") ;;
    esac
  done < <(git diff --name-only --diff-filter=U -z)
  if (( ${#unresolved[@]} )); then
    echo 'Upstream merge needs manual resolution:' >&2
    printf '%s\n' "${unresolved[@]}" >&2
    exit 1
  fi
fi

cp -- "$workflow_snapshot" "$workflow_path"
python3 "$policy_dir/workflow_policy.py" --apply
python3 "$policy_dir/download_policy.py" --apply
python3 "$policy_dir/test_download_policy.py"
git add -- "$region_path" .github/workflows
if git rev-parse -q --verify MERGE_HEAD >/dev/null; then
  git commit -m "Merge HMCL upstream ${upstream_sha:0:12} with unrestricted downloads"
elif ! git diff --cached --quiet; then
  git commit -m 'Restore unrestricted download policy'
fi
git merge-base --is-ancestor "$upstream_sha" HEAD
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "upstream_sha=$upstream_sha" >> "$GITHUB_OUTPUT"
fi
