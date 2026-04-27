#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/dist/ForMyDJ.app"
CONTENTS="$APP/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
LAUNCHER_C="$ROOT/dist/launcher.c"

rm -rf "$APP"
mkdir -p "$MACOS" "$RESOURCES"
cp -R "$ROOT/app" "$RESOURCES/app"

cat > "$CONTENTS/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>ForMyDJ</string>
  <key>CFBundleDisplayName</key>
  <string>ForMyDJ</string>
  <key>CFBundleIdentifier</key>
  <string>com.slavaporollo.formydj</string>
  <key>CFBundleVersion</key>
  <string>0.1.0</string>
  <key>CFBundleShortVersionString</key>
  <string>0.1.0</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleExecutable</key>
  <string>ForMyDJ</string>
  <key>LSMinimumSystemVersion</key>
  <string>12.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
PLIST

cat > "$LAUNCHER_C" <<'C'
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    char executable[PATH_MAX];
    char macos_dir[PATH_MAX];
    char app_dir[PATH_MAX];
    char desktop_py[PATH_MAX];

    if (realpath(argv[0], executable) == NULL) {
        return 1;
    }

    strncpy(macos_dir, executable, sizeof(macos_dir));
    char *last_slash = strrchr(macos_dir, '/');
    if (last_slash == NULL) {
        return 1;
    }
    *last_slash = '\0';

    snprintf(app_dir, sizeof(app_dir), "%s/../Resources/app", macos_dir);
    snprintf(desktop_py, sizeof(desktop_py), "%s/desktop.py", app_dir);

    if (chdir(app_dir) != 0) {
        return 1;
    }

    execl("/usr/bin/python3", "python3", desktop_py, (char *)NULL);
    return 1;
}
C

/usr/bin/clang -arch arm64 -mmacosx-version-min=12.0 "$LAUNCHER_C" -o "$MACOS/ForMyDJ"
rm -f "$LAUNCHER_C"

echo "Built $APP"
