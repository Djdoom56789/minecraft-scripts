#!/usr/bin/env sh
# Regenerates the textures and packages one zip per supported game version:
#   dist/GreenPvP.zip         Minecraft 26.3
#   dist/GreenPvP-1.21.1.zip  Minecraft 1.21 / 1.21.1
set -eu
cd "$(dirname "$0")"
rm -rf pack pack-1.21.1
python3 generate.py pack 26.3
python3 generate.py pack-1.21.1 1.21.1
python3 preview.py preview.png pack 26.3 >/dev/null
mkdir -p dist
rm -f dist/GreenPvP.zip dist/GreenPvP-1.21.1.zip
(cd pack && zip -qr ../dist/GreenPvP.zip .)
(cd pack-1.21.1 && zip -qr ../dist/GreenPvP-1.21.1.zip .)
echo "Built $(pwd)/dist/GreenPvP.zip (26.3) and dist/GreenPvP-1.21.1.zip"
# Everything someone needs to run greenify on their own computer.
rm -f dist/GreenEverything-builder.zip
zip -qr dist/GreenEverything-builder.zip greenify.py greenify.bat greenify.sh pack pack-1.21.1
echo "Built $(pwd)/dist/GreenEverything-builder.zip"
