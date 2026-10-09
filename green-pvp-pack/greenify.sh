#!/usr/bin/env sh
# Builds dist/GreenEverything.zip from your own Minecraft install (macOS/Linux).
set -eu
cd "$(dirname "$0")"
python3 -m pip install --user --quiet pillow numpy 2>/dev/null || true
python3 greenify.py "$@"
