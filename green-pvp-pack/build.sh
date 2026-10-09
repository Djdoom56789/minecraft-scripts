#!/usr/bin/env sh
# Regenerates the textures and packages dist/GreenPvP.zip.
set -eu
cd "$(dirname "$0")"
python3 generate.py pack
python3 preview.py preview.png pack >/dev/null
mkdir -p dist
rm -f dist/GreenPvP.zip
(cd pack && zip -qr ../dist/GreenPvP.zip .)
echo "Built $(pwd)/dist/GreenPvP.zip"
# Everything someone needs to run greenify on their own computer.
rm -f dist/GreenEverything-builder.zip
zip -qr dist/GreenEverything-builder.zip greenify.py greenify.bat greenify.sh pack
echo "Built $(pwd)/dist/GreenEverything-builder.zip"
