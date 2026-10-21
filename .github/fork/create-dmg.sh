#!/usr/bin/env bash
# Retry transient disk-image service contention without hiding packaging errors.
set -euo pipefail

app="$1"
destination="$2"
log="$(mktemp)"
trap 'rm -f -- "$log"' EXIT

for attempt in 1 2 3; do
  if LC_ALL=C hdiutil create -volname HMCL -srcfolder "$app" -ov -format UDZO "$destination" >"$log" 2>&1; then
    cat "$log"
    hdiutil verify "$destination"
    exit 0
  else
    status=$?
  fi
  cat "$log" >&2
  if [[ "$attempt" == 3 ]] || ! grep -Fqi 'Resource busy' "$log"; then
    exit "$status"
  fi
  delay=$((attempt * 5))
  echo "Disk-image service busy; retrying in ${delay}s (attempt $((attempt + 1))/3)." >&2
  sleep "$delay"
done
