#!/usr/bin/env sh
# Packages the shader pack as dist/GreenShaders.zip for OptiFine or Iris.
set -eu
cd "$(dirname "$0")"
mkdir -p dist
rm -f dist/GreenShaders.zip
zip -qr dist/GreenShaders.zip shaders
echo "Built $(pwd)/dist/GreenShaders.zip"
