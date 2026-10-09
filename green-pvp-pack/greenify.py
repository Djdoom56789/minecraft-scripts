#!/usr/bin/env python3
"""Builds "Green Everything": every item, block, particle and mob texture in
Minecraft turned green, with the hand-made Green PvP textures on top.

Mojang's textures can't be redistributed, so this runs on your computer and
reads them from your own copy of the game.

How the green is applied: hues are squeezed toward green instead of painted
over, so things that were different colors stay different. Red turns yellow-
green, blue turns teal, grays get a green cast, and brightness never changes.
Textures whose color carries meaning, or that the game tints itself, are left
alone (see SKIP below).

Usage:
    python3 greenify.py                       # finds .minecraft, uses 1.21.1
    python3 greenify.py --version 1.21.4
    python3 greenify.py --jar path/to/1.21.1.jar --out GreenEverything.zip

Requires Python 3.9+, Pillow and numpy (pip install pillow numpy).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
GREEN_HUE = 1 / 3

# How strongly each texture folder is pulled toward green (0 = unchanged,
# 1 = every hue becomes green). Lower values keep more of the original
# colors, which helps tell things apart.
LEAN = {
    "item": 0.5,
    "block": 0.45,
    "particle": 0.55,
    "entity": 0.35,
}

# Individual textures that get their own strength.
LEAN_OVERRIDES = {
    "entity/end_crystal/end_crystal_beam.png": 1.0,
    "block/obsidian.png": 1.0,
    "block/crying_obsidian.png": 1.0,
}

# Minimum saturation, so grays (stone, iron, cobwebs...) pick up a green cast.
GRAY_CAST = 0.18

# Textures to leave untouched, matched against "folder/path.png".
SKIP = [
    # The color tells you what it is.
    r"^item/(potion|splash_potion|lingering_potion|tipped_arrow).*",
    r"^item/.*spawn_egg.*",
    r"^item/firework_star_overlay",
    r"^item/filled_map_markings",
    r"^entity/(banner|shield)/",  # pattern masks tinted by dye
    r"^entity/banner_base", r"^entity/shield_base\.png",
    r"^trims/",                   # armor trim material colors
    # The game tints these itself (dye, biome or redstone power).
    r"^item/leather_(helmet|chestplate|leggings|boots|horse_armor)\.png$",
    r"^item/wolf_armor_overlay",
    r"^block/(grass_block_top|grass_block_side_overlay|short_grass|tall_grass_.*|fern|large_fern_.*|vine"
    r"|lily_pad|sugar_cane|water_.*|redstone_dust_.*|.*_stem|attached_.*_stem"
    r"|(oak|spruce|birch|jungle|acacia|dark_oak|mangrove)_leaves)\.png$",
    # Player skins and capes belong to the players.
    r"^entity/player/", r"^entity/cape",
]
SKIP_RE = [re.compile(p) for p in SKIP]


def to_green(rgba: np.ndarray, lean: float) -> np.ndarray:
    """Squeezes hues toward green while keeping lightness. rgba: HxWx4 uint8."""
    rgb = rgba[..., :3].astype(np.float64) / 255.0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    maxc, minc = rgb.max(-1), rgb.min(-1)
    light = (maxc + minc) / 2
    delta = maxc - minc
    chroma = delta > 1e-6

    sat = np.zeros_like(light)
    denom = np.where(light < 0.5, maxc + minc, 2.0 - maxc - minc)
    np.divide(delta, denom, out=sat, where=chroma & (denom > 1e-6))

    safe = np.where(chroma, delta, 1.0)
    rc, gc, bc = (maxc - r) / safe, (maxc - g) / safe, (maxc - b) / safe
    hue = np.where(r == maxc, bc - gc, np.where(g == maxc, 2.0 + rc - bc, 4.0 + gc - rc))
    hue = np.where(chroma, (hue / 6.0) % 1.0, GREEN_HUE)

    offset = (hue - GREEN_HUE + 0.5) % 1.0 - 0.5
    hue = (GREEN_HUE + offset * (1.0 - lean)) % 1.0
    # Magenta sits opposite green, where the squeeze would split neighbouring
    # purples into orange and blue; fade saturation at that seam instead.
    seam = np.clip((np.abs(offset) - 0.40) / 0.10, 0.0, 1.0)
    sat = sat * (1.0 - 0.75 * seam * seam * (3 - 2 * seam))
    sat = np.maximum(sat, GRAY_CAST * min(1.0, lean * 2))

    q = np.where(light < 0.5, light * (1 + sat), light + sat - light * sat)
    p = 2 * light - q

    def channel(t):
        t = t % 1.0
        return np.where(t < 1 / 6, p + (q - p) * 6 * t,
                        np.where(t < 0.5, q, np.where(t < 2 / 3, p + (q - p) * (2 / 3 - t) * 6, p)))

    out = rgba.copy()
    out[..., 0] = np.clip(np.round(channel(hue + 1 / 3) * 255), 0, 255)
    out[..., 1] = np.clip(np.round(channel(hue) * 255), 0, 255)
    out[..., 2] = np.clip(np.round(channel(hue - 1 / 3) * 255), 0, 255)
    return out


def lean_for(rel: str) -> float | None:
    """Strength for a texture path like "block/stone.png", or None to skip it."""
    if rel in LEAN_OVERRIDES:
        return LEAN_OVERRIDES[rel]
    if any(p.search(rel) for p in SKIP_RE):
        return None
    folder = rel.split("/", 1)[0]
    if folder == "entity" and rel.startswith("entity/equipment/"):
        return None  # worn armor comes from the custom pack
    return LEAN.get(folder)


def default_minecraft_dir() -> Path:
    if sys.platform.startswith("win"):
        return Path(os.environ.get("APPDATA", Path.home())) / ".minecraft"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "minecraft"
    return Path.home() / ".minecraft"


def build(jar: Path, custom: Path, out: Path) -> dict[str, int]:
    prefix = "assets/minecraft/textures/"
    stats = {"recolored": 0, "skipped": 0, "custom": 0}
    custom_files = {p.relative_to(custom).as_posix(): p for p in custom.rglob("*") if p.is_file()}

    with zipfile.ZipFile(jar) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        names = set(src.namelist())
        for name in sorted(names):
            if not name.startswith(prefix) or not name.endswith(".png"):
                continue
            rel = name[len(prefix):]
            if name in custom_files:
                continue  # hand-made version wins
            lean = lean_for(rel)
            if lean is None:
                stats["skipped"] += 1
                continue
            img = Image.open(io.BytesIO(src.read(name))).convert("RGBA")
            green = Image.fromarray(to_green(np.asarray(img), lean), "RGBA")
            buf = io.BytesIO()
            green.save(buf, "PNG", optimize=True)
            dst.writestr(name, buf.getvalue())
            # Keep animations (water, lava, fire, portals, compasses...).
            meta = name + ".mcmeta"
            if meta in names and meta not in custom_files:
                dst.writestr(meta, src.read(meta))
            stats["recolored"] += 1

        for rel, path in sorted(custom_files.items()):
            if rel.startswith("green_world_"):
                continue  # textures are already green; the live shader would double it
            data = path.read_bytes()
            if rel == "pack.mcmeta":
                meta = json.loads(data)
                meta["pack"]["description"] = "Green Everything: the whole game in green"
                meta.pop("overlays", None)
                data = (json.dumps(meta, indent=2) + "\n").encode()
            dst.writestr(rel, data)
            stats["custom"] += 1
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", default="1.21.1", help="Minecraft version to read (default 1.21.1)")
    parser.add_argument("--minecraft-dir", type=Path, default=default_minecraft_dir(),
                        help="your .minecraft folder (found automatically)")
    parser.add_argument("--jar", type=Path, help="path to the client jar, instead of --version/--minecraft-dir")
    parser.add_argument("--custom", type=Path, default=HERE / "pack",
                        help="hand-made Green PvP textures to put on top (default: ./pack)")
    parser.add_argument("--out", type=Path, default=HERE / "dist" / "GreenEverything.zip")
    args = parser.parse_args()

    jar = args.jar or args.minecraft_dir / "versions" / args.version / f"{args.version}.jar"
    if not jar.is_file():
        print(f"Can't find the Minecraft jar at {jar}.\n"
              f"Launch Minecraft {args.version} once from the official launcher so it downloads, "
              "or pass --jar.", file=sys.stderr)
        return 1
    if not (args.custom / "pack.mcmeta").is_file():
        print(f"Can't find the Green PvP pack at {args.custom}. Run generate.py first.", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    stats = build(jar, args.custom, args.out)
    print(f"Wrote {args.out}: {stats['recolored']} textures turned green, {stats['custom']} custom files, "
          f"{stats['skipped']} left as-is (potions, dyes, biome-tinted, skins).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
