#!/usr/bin/env bash
# Package the verified cross-platform JAR with a local JavaFX runtime for this CPU.
set -euo pipefail

jar_path="$1"
build_sha="$2"
arch="$3"
package_root="${RUNNER_TEMP:?}/hmcl-macos-$arch"
mkdir -p "$package_root/input" "$package_root/output" "$package_root/HMCL.iconset"
cp "$jar_path" "$package_root/input/"
icon=HMCL/image/hmcl.png
for size in 16 32 128 256 512; do
  sips -z "$size" "$size" "$icon" --out "$package_root/HMCL.iconset/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  sips -z "$double" "$double" "$icon" --out "$package_root/HMCL.iconset/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$package_root/HMCL.iconset" -o "$package_root/HMCL.icns"

# Native launchers do not use java -jar, so forward the JAR's module opens explicitly.
java_options=(--java-options '--add-modules=javafx.controls,javafx.fxml,javafx.web,javafx.swing')
while IFS= read -r module; do
  java_options+=(--java-options "--add-opens=$module=ALL-UNNAMED")
done < <(python3 - "$jar_path" <<'PY'
import sys
import zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    properties = archive.read('assets/hmcl.properties').decode('utf-8')
    value = next(line.split('=', 1)[1] for line in properties.splitlines() if line.startswith('hmcl.add-opens='))
    print('\n'.join(value.split()))
PY
)
version_root="$(awk -F= '$1 == "versionRoot" {print $2}' config/project.properties)"

# Include the JDK's JavaFX modules: the app works without a separately installed JRE.
jpackage \
  --type app-image \
  --input "$package_root/input" \
  --main-jar "$(basename "$jar_path")" \
  --name HMCL \
  --app-version "${version_root:?}.${GITHUB_RUN_NUMBER:?}" \
  --vendor xiaoka520 \
  --description 'HMCL unofficial fork with unrestricted downloads' \
  --icon "$package_root/HMCL.icns" \
  "${java_options[@]}" \
  --module-path "$JAVA_HOME/jmods" \
  --add-modules ALL-MODULE-PATH \
  --jlink-options '--strip-debug --no-man-pages --no-header-files' \
  --dest "$package_root/output"

app="$package_root/output/HMCL.app"
test -x "$app/Contents/MacOS/HMCL"
"$app/Contents/runtime/Contents/Home/bin/java" --list-modules | grep '^javafx.controls@'
codesign --force --deep --sign - "$app"
codesign --verify --deep --strict "$app"
mkdir -p dist
artifact_base="HMCL-unrestricted-macos-$arch-dmg-$build_sha"
bash "$(dirname -- "${BASH_SOURCE[0]}")/create-dmg.sh" "$app" "dist/$artifact_base.dmg"
