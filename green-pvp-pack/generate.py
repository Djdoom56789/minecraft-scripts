#!/usr/bin/env python3
"""Generates the Green PvP resource pack.

Every texture is drawn from scratch here (no Mojang assets are copied), so the
pack can be rebuilt or restyled by editing palettes and shapes below.

Design rules, so PvP gear stays readable at a glance:
  * Each material keeps its own hue and brightness: wood brown, stone gray,
    iron near-white, gold yellow, diamond aqua, netherite near-black. Green is
    only applied as an accent (guards, pommels, trims, gems, vines).
  * Armor bases lean slightly green but keep the same brightness ordering as
    vanilla, and chainmail keeps its see-through mesh.
  * Item shapes (sword vs. axe vs. mace...) match vanilla silhouettes.
  * Potions and tipped arrows are left alone: their colors encode the effect.
  * Animations (green glint on weapons, lightning on the trident, aura on
    the totem) only add green on top for part of each loop.

Usage: python3 generate.py [output_dir]   (default: ./pack)
To make the rest of the game green as well, see greenify.py.
Requires Pillow.
"""

from __future__ import annotations

import colorsys
import json
import math
import random
import sys
from pathlib import Path

from PIL import Image

# --------------------------------------------------------------------------
# Palettes
# --------------------------------------------------------------------------


def rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha


def palette(light, mid, dark, outline, shine=None):
    return {
        "light": rgba(light),
        "mid": rgba(mid),
        "dark": rgba(dark),
        "outline": rgba(outline),
        "shine": rgba(shine or light),
    }


GREEN = {
    "glow": rgba("#d4ff8a"),
    "light": rgba("#7ddc4f"),
    "mid": rgba("#36a93d"),
    "dark": rgba("#1d6a26"),
    "outline": rgba("#0b2a10"),
}

HANDLE = palette("#5c4838", "#3d2e23", "#251b14", "#0e0a07")
POMMEL = palette("#5a6660", "#3a4440", "#262d2a", "#0c0f0e")
STRING = palette("#f2f2e6", "#d9d9c8", "#b0b09c", "#55554a")
BOW_WOOD = palette("#a8763e", "#7f5426", "#5a3a18", "#2a1a09")

# Tool and weapon materials. Order of brightness is preserved from vanilla.
TOOL = {
    "wooden": palette("#cfa266", "#a2743a", "#6e4c22", "#33210e"),
    "stone": palette("#b4b9b1", "#8a9087", "#5f655d", "#262a25"),
    "iron": palette("#f6faf6", "#cdd7cf", "#8e9b93", "#38413c", shine="#ffffff"),
    "golden": palette("#fff68f", "#f4c431", "#b98719", "#4f3406", shine="#fffbe0"),
    "diamond": palette("#c6fff4", "#4fe4d1", "#1f9e91", "#0a4540", shine="#ffffff"),
    "netherite": palette("#717c74", "#48524b", "#2c332e", "#0c0f0d"),
}

# How far armor colors are pulled toward green (0 = vanilla hues, 1 = all
# green). Lightness is never changed, so the materials keep vanilla's
# brightness order and stay tellable apart.
ARMOR_GREEN_LEAN = 0.35
GREEN_HUE = 120 / 360


def lean_green(pal, amount=ARMOR_GREEN_LEAN):
    leaned = {}
    for key, (r, g, b, a) in pal.items():
        h, l, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        delta = (GREEN_HUE - h + 0.5) % 1.0 - 0.5  # shortest way around the hue wheel
        h = (h + delta * amount) % 1.0
        sat = min(1.0, sat + (0.25 * amount if sat < 0.25 else 0.0))  # give grays a green cast
        nr, ng, nb = colorsys.hls_to_rgb(h, l, sat)
        leaned[key] = (round(nr * 255), round(ng * 255), round(nb * 255), a)
    return leaned


# Armor materials: (item prefix, worn texture name, palette)
ARMOR = {
    "leather": ("leather", palette("#ffffff", "#d6d6d6", "#a3a3a3", "#4d4d4d")),
    "chainmail": ("chainmail", lean_green(palette("#c3cfc3", "#93a293", "#647364", "#283028"))),
    "iron": ("iron", lean_green(palette("#f2f8f2", "#c7d6c9", "#8fa293", "#36423a", shine="#ffffff"))),
    # Gold leans less: past ~0.2 it turns lime and stops reading as gold.
    "golden": ("gold", lean_green(palette("#fff68f", "#f4c431", "#b98719", "#4f3406", shine="#fffbe0"), 0.2)),
    "diamond": ("diamond", lean_green(palette("#c2fff0", "#4ee4c6", "#1f9e8a", "#0a453c", shine="#ffffff"))),
    "netherite": ("netherite", lean_green(palette("#5b6a5f", "#3b463e", "#262e28", "#0b0e0c"))),
}

LEATHER_DEFAULT_TINT = (0xA0, 0x65, 0x40)

MACE = palette("#dbe2dd", "#9ba8a0", "#5f6a63", "#222826", shine="#ffffff")
TRIDENT = palette("#aef3dc", "#53b99c", "#2b7b67", "#0d3329", shine="#e8fff7")
PEARL = palette("#b8f0d0", "#3aa071", "#0f4a3a", "#062019", shine="#ffffff")
SHIELD_WOOD = palette("#8a6034", "#6d4a26", "#4f3519", "#24170a")

# --------------------------------------------------------------------------
# Sprite helpers
# --------------------------------------------------------------------------


# Marks pixels added by Sprite.outline(), so animations can tell edges apart.
OUTLINE: dict = {}


class Sprite:
    """Sparse pixel canvas that remembers which palette each pixel came from,
    so outlines can use the right outline color."""

    def __init__(self, width: int = 16, height: int = 16):
        self.w, self.h = width, height
        self.px: dict[tuple[int, int], tuple[tuple[int, int, int, int], dict | None]] = {}

    def put(self, x, y, color, pal=None):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[(x, y)] = (color, pal)

    def outline(self):
        added = {}
        for (x, y), (_, pal) in self.px.items():
            if pal is None or pal is OUTLINE:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if 0 <= n[0] < self.w and 0 <= n[1] < self.h and n not in self.px and n not in added:
                    added[n] = (pal["outline"], OUTLINE)
        self.px.update(added)
        return self

    def image(self) -> Image.Image:
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        for (x, y), (color, _) in self.px.items():
            img.putpixel((x, y), color)
        return img


def diagonal_cells():
    """Yields (x, y, s, d) for a 16x16 sprite, where s runs along the
    bottom-left -> top-right diagonal (-15..15) and d across it."""
    for y in range(16):
        for x in range(16):
            yield x, y, x - y, x + y - 15


def xy(s, d):
    return (s + d + 15) // 2, (d - s + 15) // 2


def line(sprite, x0, y0, x1, y1, color, pal):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        sprite.put(x0, y0, color, pal)
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def from_ascii(rows, pal, green=GREEN, extra=None):
    """Builds a sprite from a 16x16 character template.

    L/M/D/o/W = material light/mid/dark/outline/shine
    e/E/G/g/k = green light/glow/mid/dark/outline
    h/H       = handle mid/dark
    """
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), "template must be 16x16"
    codes = {
        "L": (pal["light"], pal), "M": (pal["mid"], pal), "D": (pal["dark"], pal),
        "o": (pal["outline"], None), "W": (pal["shine"], pal),
        "e": (green["light"], green), "E": (green["glow"], green), "G": (green["mid"], green),
        "g": (green["dark"], green), "k": (green["outline"], None),
        "h": (HANDLE["mid"], HANDLE), "H": (HANDLE["dark"], HANDLE),
    }
    codes.update(extra or {})
    sprite = Sprite()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                color, p = codes[ch]
                sprite.put(x, y, color, p)
    return sprite


# --------------------------------------------------------------------------
# Weapons
# --------------------------------------------------------------------------


def draw_handle(sp, s_from, s_to, pal=HANDLE):
    for x, y, s, d in diagonal_cells():
        if s_from <= s <= s_to and abs(d) <= 1:
            sp.put(x, y, pal["light"] if (s // 2) % 2 == 0 else pal["dark"], pal)


def draw_vine_pommel(sp, s_center):
    """Dark metal pommel with an emerald and two small vine curls."""
    for x, y, s, d in diagonal_cells():
        if abs(s - s_center) <= 1 and abs(d) <= 1:
            sp.put(x, y, POMMEL["mid"] if d <= 0 else POMMEL["dark"], POMMEL)
    sp.put(*xy(s_center + 1, 0) if (s_center + 1) % 2 else xy(s_center, 1), GREEN["glow"], GREEN)
    for s, d, tone in ((s_center + 1, -2, "light"), (s_center + 1, 2, "mid")):
        if (s + d) % 2:
            sp.put(*xy(s, d), GREEN[tone], GREEN)
        else:
            sp.put(*xy(s + 1, d), GREEN[tone], GREEN)


def sword(pal):
    sp = Sprite()
    for x, y, s, d in diagonal_cells():
        if (-3 <= s <= 11 and abs(d) <= 2) or (s == 12 and abs(d) == 1) or (s == 13 and d == 0):
            if s == 13 or d <= -1:
                tone = "light"
            elif d == 0:
                tone = "dark" if s < 11 else "light"  # fuller down the middle
            else:
                tone = "mid"
            sp.put(x, y, pal[tone], pal)
    # Vines creeping up the base of the blade, as in the reference art.
    for s, d, tone in ((-3, 0, "light"), (-2, 1, "mid"), (-1, -2, "glow"), (0, -1, "light")):
        sp.put(*xy(s, d), GREEN[tone], GREEN)
    # Crossguard with an emerald in the middle and a vine curl at each tip.
    for x, y, s, d in diagonal_cells():
        if s in (-5, -4) and abs(d) <= 4:
            tone = "glow" if abs(d) <= 1 else ("light" if d < 0 else "mid")
            sp.put(x, y, GREEN[tone], GREEN)
    for s, d, tone in ((-3, -5, "light"), (-6, 5, "mid")):
        sp.put(*xy(s, d), GREEN[tone], GREEN)
    draw_handle(sp, -12, -6)
    draw_vine_pommel(sp, -14)
    return sp.outline()


def axe(pal):
    sp = Sprite()
    draw_handle(sp, -13, 6)
    head_rows = {2: (2, 5), 3: (1, 5), 4: (0, 5), 5: (-1, 5), 6: (-1, 5), 7: (-1, 4), 8: (0, 3)}
    for x, y, s, d in diagonal_cells():
        k = -d
        if k in head_rows and head_rows[k][0] <= s <= head_rows[k][1]:
            tone = "light" if k >= 7 else ("mid" if k >= 4 else "dark")
            sp.put(x, y, pal[tone], pal)
        elif 1 <= d <= 3 and 2 <= s <= 5:  # back of the head
            sp.put(x, y, pal["mid" if d < 3 else "dark"], pal)
        elif abs(d) <= 1 and 2 <= s <= 5:  # vine binding head to handle
            sp.put(x, y, GREEN["mid" if s % 2 else "light"], GREEN)
    sp.put(*xy(1, -4), GREEN["glow"], GREEN)  # emerald set in the head
    for s, d, tone in ((-13, 0, "glow"), (-12, -1, "light"), (-12, 1, "mid"), (-11, 2, "light"), (-11, -2, "dark")):
        sp.put(*xy(s, d), GREEN[tone], GREEN)
    return sp.outline()


def mace():
    sp = Sprite()
    draw_handle(sp, -13, 3)
    cs, cd = 8, 0
    for x, y, s, d in diagonal_cells():
        r2 = ((s - cs) ** 2 + (d - cd) ** 2) / 2
        spike = (abs(d - cd) <= 0 and abs(s - cs) == 5) or (abs(s - cs) <= 0 and abs(d - cd) == 5)
        if r2 <= 9 or spike:
            tone = "light" if d < -1 else ("mid" if d <= 1 else "dark")
            sp.put(x, y, MACE[tone], MACE)
    sp.put(*xy(cs + 1, cd), GREEN["glow"], GREEN)
    sp.put(*xy(cs, cd - 1), GREEN["light"], GREEN)
    for x, y, s, d in diagonal_cells():
        if s in (3, 4) and abs(d) <= 2:
            sp.put(x, y, GREEN["mid" if d >= 0 else "light"], GREEN)
    for s, d, tone in ((-13, 0, "glow"), (-12, 1, "light"), (-12, -1, "mid")):
        sp.put(*xy(s, d), GREEN[tone], GREEN)
    return sp.outline()


def trident():
    sp = Sprite()
    for x, y, s, d in diagonal_cells():
        if -13 <= s <= 5 and abs(d) <= 1:
            sp.put(x, y, TRIDENT["mid" if d <= 0 else "dark"], TRIDENT)
        elif s in (5, 6) and abs(d) <= 4:
            sp.put(x, y, TRIDENT["light" if d < 0 else "mid"], TRIDENT)
        elif 7 <= s <= 13 and abs(d) <= 1:
            sp.put(x, y, TRIDENT["light" if d <= 0 else "mid"], TRIDENT)
        elif 7 <= s <= 11 and abs(d) in (3, 4):
            sp.put(x, y, TRIDENT["light" if d < 0 else "mid"], TRIDENT)
    for s, d, tone in ((5, 0, "glow"), (4, 1, "light"), (-13, 0, "light"), (-12, 1, "mid"), (-1, 0, "mid"), (-3, 0, "light")):
        sp.put(*xy(s, d), GREEN[tone], GREEN)
    return sp.outline()


def arrow_sprite(sp, tail, head, head_pal):
    """Draws an arrow from tail (x, y) to head (x, y) along a 45 degree line."""
    (tx, ty), (hx, hy) = tail, head
    step_x = 1 if hx > tx else -1
    step_y = 1 if hy > ty else -1
    length = abs(hx - tx)
    for i in range(length + 1):
        x, y = tx + i * step_x, ty + i * step_y
        if i >= length - 1:
            sp.put(x, y, head_pal["light"], head_pal)
        elif i <= 2:
            sp.put(x, y, BOW_WOOD["mid"], BOW_WOOD)
            sp.put(x - step_x, y, GREEN["light" if i % 2 else "mid"], GREEN)  # fletching
            sp.put(x, y - step_y, GREEN["mid" if i % 2 else "light"], GREEN)
        else:
            sp.put(x, y, BOW_WOOD["light"], BOW_WOOD)
    # Arrowhead barbs.
    bx, by = hx - 2 * step_x, hy - 2 * step_y
    sp.put(bx + step_x, by, head_pal["mid"], head_pal)
    sp.put(bx, by + step_y, head_pal["mid"], head_pal)
    sp.put(hx - step_x, hy, head_pal["dark"], head_pal)
    sp.put(hx, hy - step_y, head_pal["dark"], head_pal)


def arrow():
    sp = Sprite()
    arrow_sprite(sp, (2, 13), (13, 2), TOOL["iron"])
    return sp.outline()


def bow(pull: int | None):
    """pull None = standby, 0-2 = drawing stages (with a nocked arrow)."""
    sp = Sprite()
    cx = cy = 16.0
    radius = 12.6
    for y in range(16):
        for x in range(16):
            dist = ((x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2) ** 0.5
            if abs(dist - radius) <= 0.75 and x + y <= 26:
                vine = (x * 7 + y * 3) % 5 == 0
                if vine:
                    sp.put(x, y, GREEN["light"], GREEN)
                else:
                    sp.put(x, y, BOW_WOOD["light" if x + y < 16 else "mid"], BOW_WOOD)
    # Grip wrap in the middle of the limb and vine tips.
    for x, y in ((6, 7), (7, 6), (7, 7), (6, 6)):
        if (x, y) in sp.px:
            sp.put(x, y, GREEN["mid"], GREEN)
    for x, y, tone in ((3, 14, "glow"), (14, 3, "glow"), (2, 13, "mid"), (13, 2, "mid")):
        sp.put(x, y, GREEN[tone], GREEN)
    sp.outline()
    # String (no outline, it's thin).
    ends = ((4, 15), (15, 4))
    if pull is None:
        line(sp, *ends[0], *ends[1], STRING["mid"], None)
    else:
        p = 10 + pull
        line(sp, *ends[0], p, p, STRING["mid"], None)
        line(sp, p, p, *ends[1], STRING["mid"], None)
        tip = 3 + pull
        arrow_sprite(sp, (p, p), (tip, tip), TOOL["iron"])
    return sp


def crossbow(state: str):
    """state: standby, pulling_0..2, arrow, firework."""
    sp = Sprite()
    for x, y, s, d in diagonal_cells():
        if -13 <= s <= 10 and abs(d) <= 1:
            sp.put(x, y, BOW_WOOD["light" if d <= 0 else "dark"], BOW_WOOD)
    # Wooden limbs across the front of the stock, curving back toward iron tips.
    limb_ends = []
    for d in range(-7, 8):
        s = 7 - round(d * d / 12)
        if (s + d) % 2 == 0:
            s -= 1
        tip = abs(d) >= 6
        p = TOOL["iron"] if tip else BOW_WOOD
        sp.put(*xy(s, d), p["light"] if d < 0 else p["mid"], p)
        if tip:
            limb_ends.append((s, d))
    sp.put(*xy(7, 0), GREEN["glow"], GREEN)
    for s, d, tone in ((-13, 0, "glow"), (-12, 1, "mid"), (-12, -1, "light"), (-5, 0, "light"), (-4, 1, "mid")):
        sp.put(*xy(s, d), GREEN[tone], GREEN)
    sp.outline()
    nock_s = {"standby": 1, "pulling_0": 0, "pulling_1": -2, "pulling_2": -4, "arrow": -4, "firework": -4}[state]
    left = xy(*min(limb_ends, key=lambda c: c[1]))
    right = xy(*max(limb_ends, key=lambda c: c[1]))
    nock = xy(nock_s if (nock_s % 2) else nock_s + 1, 0)
    line(sp, *left, *nock, STRING["mid"], None)
    line(sp, *nock, *right, STRING["mid"], None)
    if state == "arrow":
        for s in range(nock_s + 1, 13):
            if s % 2:
                sp.put(*xy(s, 0), BOW_WOOD["light"], None)
        sp.put(*xy(13, 0), TOOL["iron"]["light"], None)
        sp.put(*xy(12, -1), TOOL["iron"]["mid"], None)
        sp.put(*xy(12, 1), TOOL["iron"]["mid"], None)
    elif state == "firework":
        red = (rgba("#e23c3c"), None)
        for s in range(nock_s + 1, 12):
            for d in (-1, 1) if s % 2 == 0 else (0,):
                sp.put(*xy(s, d), *red)
        sp.put(*xy(12, -1), rgba("#f0f0f0"), None)
        sp.put(*xy(12, 1), rgba("#f0f0f0"), None)
        sp.put(*xy(13, 0), rgba("#f0f0f0"), None)
    return sp


# --------------------------------------------------------------------------
# Misc PvP items
# --------------------------------------------------------------------------

# Totem of undying drawn from the player's skin: gold crown with four gems,
# green face, black suit with white collar, red tie and yellow buttons,
# white cuffs and green hands, in the totem's arms-out pose.
SKIN_GREEN = palette("#4f9138", "#346d27", "#22501a", "#0b1f08")
CROWN = palette("#f6e44c", "#e4cc38", "#b49a1c", "#3d2f04")
SUIT = palette("#2c2c2c", "#151515", "#0b0b0b", "#08200c")
SHIRT = palette("#ffffff", "#ececec", "#c4c4c4", "#08200c")

TOTEM_ROWS = [
    "................",
    ".....Y.YY.Y.....",
    "....YPYNBYRY....",
    "....LGGGGGGD....",
    "....LKKGGKKD....",
    "....LKKGGKKD....",
    "....LGGGGGGD....",
    "....LGKKKKGD....",
    "......WTTW......",
    ".HWSSSSTTSSSSWH.",
    ".HWSSSSUTSSSSWH.",
    ".....SsSSSS.....",
    ".....SsUSSS.....",
    ".....Ss..SS.....",
    ".....SS..SS.....",
    "................",
]

TOTEM_CODES = {
    "Y": (CROWN["mid"], CROWN), "y": (CROWN["dark"], CROWN),
    "P": (rgba("#c63ad6"), CROWN), "N": (rgba("#3cc43c"), CROWN),
    "B": (rgba("#2e6fe0"), CROWN), "R": (rgba("#f07060"), CROWN),
    "L": (SKIN_GREEN["light"], SKIN_GREEN), "G": (SKIN_GREEN["mid"], SKIN_GREEN),
    "D": (SKIN_GREEN["dark"], SKIN_GREEN), "K": (rgba("#0d1a0b"), SKIN_GREEN),
    "H": (SKIN_GREEN["mid"], SKIN_GREEN),
    "W": (SHIRT["mid"], SHIRT), "T": (rgba("#8c1414"), SHIRT), "U": (rgba("#dcd43c"), SUIT),
    "S": (SUIT["mid"], SUIT), "s": (SUIT["light"], SUIT),
}


def totem():
    return from_ascii(TOTEM_ROWS, SUIT, extra=TOTEM_CODES).outline()

GOLDEN_APPLE_ROWS = [
    "................",
    ".........kk.....",
    "........kGEk....",
    ".......okGk.....",
    "...ooooHoooo....",
    "..oLLLLLMMMMo...",
    ".oLWWLLLMMMMDo..",
    ".oLWLLLMMMMMDo..",
    ".oLLLLMMMMMMDo..",
    ".oLLLMMMMMMMDo..",
    ".oLMMMMMMMMDDo..",
    "..oMMMMMMMDDo...",
    "..oDMMMMMDDDo...",
    "...oDDooDDDo....",
    "....ooo.ooo.....",
    "................",
]

ENDER_PEARL_ROWS = [
    "................",
    "................",
    ".....oooooo.....",
    "....oLLeGGGo....",
    "...oLWeGGGGgo...",
    "...oLeGGGgGgo...",
    "...oeGGgEgGgo...",
    "...oGGgEEgGDo...",
    "...oGgGgggGDo...",
    "...oGGGgGGDDo...",
    "....oGGGGDDo....",
    ".....oooooo.....",
    "................",
    "................",
    "................",
    "................",
]

# --------------------------------------------------------------------------
# Armor icons
# --------------------------------------------------------------------------

ARMOR_ICONS = {
    "helmet": [
        "................",
        "................",
        "................",
        "....oooooooo....",
        "...oLLLLLLLMo...",
        "..oLLMMMMMMMDo..",
        "..oLMMMMMMMMDo..",
        "..ogGGeEEeGGgo..",
        "..oLMDooooLMDo..",
        "..oLMo....oMDo..",
        "..oMDo....oDDo..",
        "..oooo....oooo..",
        "................",
        "................",
        "................",
        "................",
    ],
    "chestplate": [
        "................",
        "..oooo....oooo..",
        ".oLLLMo..oLLMDo.",
        ".oLMMMLooLMMMDo.",
        ".oLMMMMLLMMMMDo.",
        ".ooDMMGeEGMMDoo.",
        "...oLMgEEgMDo...",
        "...oLMMggMMDo...",
        "...oLMMMMMMDo...",
        "...oLMMMMMMDo...",
        "...oLMMMMMMDo...",
        "...oDDDDDDDDo...",
        "...oooooooooo...",
        "................",
        "................",
        "................",
    ],
    "leggings": [
        "................",
        "..oooooooooooo..",
        "..ogGGeEEeGGgo..",
        "..oLMMMMMMMMDo..",
        "..oLMMMooMMMDo..",
        "..oLMDo..oLMDo..",
        "..oLMDo..oLMDo..",
        "..oGeEo..oGeEo..",
        "..oLMDo..oLMDo..",
        "..oLMDo..oLMDo..",
        "..oLMDo..oLMDo..",
        "..oDDDo..oDDDo..",
        "..ooooo..ooooo..",
        "................",
        "................",
        "................",
    ],
    "boots": [
        "................",
        "................",
        "................",
        "................",
        "................",
        "..oooo....oooo..",
        "..oGeo....oGeo..",
        "..oLMo....oLMo..",
        "..oLMo....oLMo..",
        ".ooLMo...ooLMo..",
        ".oLMMo...oLMMo..",
        ".oLMMo...oLMMo..",
        ".oDDDo...oDDDo..",
        ".ooooo...ooooo..",
        "................",
        "................",
    ],
}

GREEN_CODES = set("eEGgk")


def armor_icon(rows, pal, chainmail=False):
    sp = from_ascii(rows, pal)
    if chainmail:  # mesh pattern so chainmail reads differently from iron
        for (x, y), (color, p) in list(sp.px.items()):
            if p is pal and color == pal["mid"] and (x + y) % 2 == 0:
                sp.put(x, y, pal["dark"], pal)
    return sp


def leather_icon(rows):
    """Leather is dye-tinted, so green goes in the untinted overlay.
    Returns (base image, overlay sprite)."""
    pal = ARMOR["leather"][1]
    base_rows = ["".join("M" if c in GREEN_CODES - {"k"} else ("o" if c == "k" else c) for c in r) for r in rows]
    overlay_rows = ["".join(c if c in GREEN_CODES else "." for c in r) for r in rows]
    return from_ascii(base_rows, pal).image(), from_ascii(overlay_rows, pal)


# --------------------------------------------------------------------------
# Worn armor (64x32 humanoid layers)
# --------------------------------------------------------------------------


def cube_faces(u, v, w, h, d):
    return {
        "top": (u + d, v, w, d),
        "bottom": (u + d + w, v, w, d),
        "right": (u, v + d, d, h),
        "front": (u + d, v + d, w, h),
        "left": (u + d + w, v + d, d, h),
        "back": (u + d + w + d, v + d, w, h),
    }


HEAD = (0, 0, 8, 8, 8)
BODY = (16, 16, 8, 12, 4)
ARM = (40, 16, 4, 12, 4)
LEG = (0, 16, 4, 12, 4)
SIDES = ("front", "back", "left", "right")


def helmet_role(face, fx, fy, fw, fh):
    if face == "bottom":
        return None
    if face == "top":
        return "base"
    if face == "front":
        if fy == 1 and fx in (3, 4):
            return "gem"
        if fy == 2:
            return "trim"
        if fy == 3 and fx in (1, 6):
            return "vine"
        if fy <= 1 or ((fx <= 1 or fx >= fw - 2) and fy <= 6):
            return "base"
        return None
    if fy == 2:
        return "trim"
    if fy == 3 and fx % 3 == 1:
        return "vine"
    return "base"


def chest_role(face, fx, fy, fw, fh):
    if face == "bottom":
        return None
    if face == "top":
        return "base"
    if face == "front":
        if fx in (3, 4) and fy in (3, 4):
            return "gem"
        if fy == 0 and 2 <= fx <= 5:
            return "trim"
        if (fx, fy) in ((2, 4), (5, 4), (3, 5), (4, 5), (3, 2), (4, 2)):
            return "vine"
    if fy == fh - 1:
        return "trim"
    if fy == fh - 2 and (fx + fy) % 3 == 0:
        return "vine"
    return "base"


def shoulder_role(face, fx, fy, fw, fh):
    if face == "bottom":
        return None
    if face == "top":
        return "base"
    if fy <= 4:
        return "base"
    if fy == 5:
        return "trim"
    if fy == 6 and fx % 2 == 0:
        return "vine"
    return None


def boot_role(face, fx, fy, fw, fh):
    if face == "top":
        return None
    if face == "bottom":
        return "dark"
    if fy == 8:
        return "trim"
    if fy == 9 and face == "front" and fx in (1, 2):
        return "gem"
    if fy > 8:
        return "base"
    return None


def legging_body_role(face, fx, fy, fw, fh):
    if face in ("top", "bottom"):
        return None
    if fy == 7:
        return "trim"
    if fy == 8 and face == "front" and fx in (3, 4):
        return "gem"
    if fy > 7:
        return "base"
    return None


def legging_leg_role(face, fx, fy, fw, fh):
    if face in ("top", "bottom"):
        return None
    if fy == 5 and face == "front":
        return "trim"
    if fy <= 9:
        return "base"
    return None


def paint_cube(img, cube, role_fn, pal, rng, chainmail=False, only_green=False, no_green=False):
    for face, (fu, fv, fw, fh) in cube_faces(*cube).items():
        for fy in range(fh):
            for fx in range(fw):
                role = role_fn(face, fx, fy, fw, fh)
                if role is None:
                    continue
                green_role = role in ("trim", "gem", "vine")
                if no_green and green_role:
                    role = "base"
                    green_role = False
                if only_green and not green_role:
                    continue
                if role == "trim":
                    color = GREEN["mid"] if (fx + fy) % 2 else GREEN["dark"]
                elif role == "gem":
                    color = GREEN["glow"] if (fx + fy) % 2 == 0 else GREEN["light"]
                elif role == "vine":
                    color = GREEN["light"]
                elif role == "dark":
                    color = pal["dark"]
                else:
                    if chainmail and fy % 2 == 1 and fx % 2 == 0:
                        continue  # mesh holes
                    if fy == 0 or fx == 0:
                        color = pal["light"]
                    elif fy == fh - 1 or fx == fw - 1:
                        color = pal["dark"]
                    else:
                        roll = rng.random()
                        color = pal["light"] if roll < 0.12 else (pal["dark"] if roll > 0.9 else pal["mid"])
                img.putpixel((fu + fx, fv + fy), color)


def armor_layers(material, pal, **kwargs):
    rng = random.Random(f"green-pvp-{material}")
    chainmail = material == "chainmail"
    layer1 = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    paint_cube(layer1, HEAD, helmet_role, pal, rng, chainmail, **kwargs)
    paint_cube(layer1, BODY, chest_role, pal, rng, chainmail, **kwargs)
    paint_cube(layer1, ARM, shoulder_role, pal, rng, chainmail, **kwargs)
    paint_cube(layer1, LEG, boot_role, pal, rng, chainmail, **kwargs)
    layer2 = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    paint_cube(layer2, BODY, legging_body_role, pal, rng, chainmail, **kwargs)
    paint_cube(layer2, LEG, legging_leg_role, pal, rng, chainmail, **kwargs)
    return layer1, layer2


# --------------------------------------------------------------------------
# Shield (entity texture, 64x64)
# --------------------------------------------------------------------------


def shield():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    rim = ARMOR["iron"][1]
    faces = cube_faces(0, 0, 12, 22, 1)
    for name, (u, v, w, h) in faces.items():
        for fy in range(h):
            for fx in range(w):
                if name in ("front", "back"):
                    border = fx in (0, w - 1) or fy in (0, h - 1)
                    if border:
                        color = rim["light"] if (fx == 0 or fy == 0) else rim["dark"]
                    else:
                        plank = (fx - 1) // 3
                        color = SHIELD_WOOD["mid"] if plank % 2 else SHIELD_WOOD["light"]
                        if (fx - 1) % 3 == 2:
                            color = SHIELD_WOOD["dark"]
                    if name == "front" and not border:
                        # Vine emblem: an emerald with leaves growing from it.
                        cx, cy = 5.5, 10.5
                        if abs(fx - cx) + abs(fy - cy) <= 1.5:
                            color = GREEN["glow"]
                        elif abs(fx - cx) + abs(fy - cy) <= 2.5:
                            color = GREEN["mid"]
                        elif fx == round(cx + (fy - cy) * 0.5) and 2 <= fy <= 19:
                            color = GREEN["dark"] if fy % 3 else GREEN["light"]
                        elif fy in (5, 16) and 2 <= fx <= 9 and (fx + fy) % 2 == 0:
                            color = GREEN["light"]
                else:
                    color = rim["mid"]
                img.putpixel((u + fx, v + fy), color)
    for name, (u, v, w, h) in cube_faces(26, 0, 2, 6, 6).items():
        for fy in range(h):
            for fx in range(w):
                img.putpixel((u + fx, v + fy), SHIELD_WOOD["dark"] if fy % 2 else SHIELD_WOOD["mid"])
    return img



# --------------------------------------------------------------------------
# Animations (vertical frame strips + .png.mcmeta, no mods needed)
# --------------------------------------------------------------------------

FRAME_TIME = 2  # game ticks per frame; the game interpolates between frames


def mix(color, target, amount):
    amount = max(0.0, min(1.0, amount))
    return tuple(round(c + (t - c) * amount) for c, t in zip(color[:3], target[:3])) + (color[3],)


def render_strip(sprite, frames, effect, extra=None):
    """Renders `frames` frames stacked vertically. effect(f, x, y, color, pal)
    recolors existing pixels; extra(f) can add pixels such as sparks."""
    strip = Image.new("RGBA", (sprite.w, sprite.h * frames), (0, 0, 0, 0))
    for f in range(frames):
        for (x, y), (color, pal) in sprite.px.items():
            strip.putpixel((x, y + f * sprite.h), effect(f, x, y, color, pal))
        for (x, y), color in (extra(f) if extra else {}).items():
            strip.putpixel((x, y + f * sprite.h), color)
    return strip


NEUTRAL = (HANDLE, POMMEL, STRING)


def weapon_glint(frames=24):
    """A green glint sweeps along the weapon (bottom-left to top-right), then
    the emeralds and vines pulse while it waits to sweep again. Material
    pixels only pick up green inside the moving band, so the material color
    stays readable for most of the cycle."""
    sweep_frames = frames * 0.6

    def effect(f, x, y, color, pal):
        s = x - y
        band = 0.0
        if f < sweep_frames:
            center = -20 + 40 * f / sweep_frames
            band = max(0.0, 1.0 - abs(s - center) / 3.5)
        pulse = 0.5 - 0.5 * math.cos(2 * math.pi * f / frames)
        if pal is GREEN:
            return mix(color, GREEN["glow"], 0.45 * pulse + 0.5 * band)
        if pal is OUTLINE:
            return mix(color, GREEN["mid"], 0.75 * band)
        if pal is None or pal in NEUTRAL:
            return mix(color, GREEN["light"], 0.3 * band)
        return mix(color, GREEN["glow"], 0.65 * band)

    return effect


def trident_storm(sprite, frames=32):
    """Special trident animation: a bolt of green energy climbs the shaft,
    the prongs flash, sparks crackle around the tips, then it fades into a
    soft glow."""
    climb_end, flash_end = 14, 24
    prongs = [(x, y) for (x, y), (_, pal) in sprite.px.items() if pal is not OUTLINE and x - y >= 7]
    spark_spots = sorted({
        (x + dx, y + dy)
        for x, y in prongs
        for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)
        if 0 <= x + dx < 16 and 0 <= y + dy < 16 and (x + dx, y + dy) not in sprite.px
    })

    def effect(f, x, y, color, pal):
        s = x - y
        if f < climb_end:
            head = -14 + 27 * f / (climb_end - 1)
            if s > head + 1.5:
                glow = 0.0
            elif s >= head - 1.5:
                glow = 0.9
            else:
                glow = max(0.0, 0.5 * (1 - (head - s) / 7))  # fading trail
        elif f < flash_end:
            decay = 1 - (f - climb_end) / (flash_end - climb_end)
            glow = (0.7 if s >= 5 else 0.3) * decay
        else:
            glow = 0.15 + 0.1 * math.sin(math.pi * (f - flash_end) / (frames - flash_end))
        target = GREEN["mid"] if pal is OUTLINE else GREEN["glow"]
        return mix(color, target, glow)

    def sparks(f):
        if not climb_end <= f < flash_end:
            return {}
        rng = random.Random(f"trident-spark-{f}")
        count = 5 if f < climb_end + 4 else 2
        chosen = rng.sample(spark_spots, min(count, len(spark_spots)))
        return {p: (GREEN["glow"] if i % 2 == 0 else GREEN["light"]) for i, p in enumerate(chosen)}

    return render_strip(sprite, frames, effect, sparks)


def totem_aura(frames=24):
    """The totem's outline breathes green; the crown gems twinkle in turn."""
    gems = [(5, 2), (7, 2), (8, 2), (10, 2)]  # P, N, B, R in TOTEM_ROWS

    def effect(f, x, y, color, pal):
        phase = 2 * math.pi * f / frames
        if pal is OUTLINE:
            return mix(color, GREEN["light"], 0.5 - 0.5 * math.cos(phase))
        if (x, y) in gems:
            lit = gems.index((x, y)) == (f * len(gems)) // frames
            return mix(color, (255, 255, 255, 255), 0.55 if lit else 0.0)
        return color

    return effect


# --------------------------------------------------------------------------
# Elytra
# --------------------------------------------------------------------------

ELYTRA = palette("#acdcc3", "#6fa58b", "#3d6c58", "#10261d", shine="#e0fff0")

ELYTRA_ROWS = [
    "................",
    "..ooooo..ooooo..",
    ".oLLLMMooMMLLLo.",
    ".oLeLMMDDMMLeLo.",
    ".oLLeMMDDMMeLLo.",
    ".oLMLeMDDMeLMLo.",
    "..oMMMeDDeMMMo..",
    "..oLMMMggMMMLo..",
    "..oLMMDooDMMLo..",
    "...oMMDooDMMo...",
    "...oMDo..oDMo...",
    "...oMDo..oDMo...",
    "....oDo..oDo....",
    "....oo....oo....",
    "................",
    "................",
]

# Torn spots for the broken elytra.
ELYTRA_TEARS = {(3, 4), (4, 5), (12, 4), (11, 5), (5, 10), (10, 11), (4, 12), (11, 12), (2, 2), (13, 3)}


def elytra_icon():
    return from_ascii(ELYTRA_ROWS, ELYTRA)


def broken_elytra_icon():
    """Torn, faded wings with no animation, so a broken elytra is obvious."""
    sp = from_ascii(ELYTRA_ROWS, ELYTRA)
    for x, y in ELYTRA_TEARS:
        sp.px.pop((x, y), None)
    for (x, y), (color, pal) in list(sp.px.items()):
        sp.put(x, y, mix(color, (90, 90, 90, 255), 0.45), pal)
    return sp.image()


def elytra_entity():
    """64x32 wing texture. Each wing is a 10x20x2 box at UV (22, 0)."""
    img = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    for name, (u, v, w, h) in cube_faces(22, 0, 10, 20, 2).items():
        for fy in range(h):
            for fx in range(w):
                if name in ("front", "back"):
                    t = fy / (h - 1)
                    color = mix(ELYTRA["light"], ELYTRA["dark"], t * 0.9)
                    # Veins fanning out from the shoulder.
                    for k in (0.18, 0.4, 0.7):
                        if fx == round(fy * k) or (name == "back" and w - 1 - fx == round(fy * k)):
                            color = GREEN["light"] if fy % 4 else GREEN["glow"]
                    if fx in (0, w - 1) or fy in (0, h - 1):
                        color = ELYTRA["outline"] if fy == h - 1 else mix(ELYTRA["dark"], GREEN["dark"], 0.5)
                    # Ragged trailing edge.
                    if fy >= h - 3 and (fx + fy) % 3 == 0:
                        continue
                else:
                    color = ELYTRA["mid"] if fy % 2 else GREEN["dark"]
                img.putpixel((u + fx, v + fy), color)
    return img


# --------------------------------------------------------------------------
# Obsidian and crying obsidian (animated block textures)
# --------------------------------------------------------------------------

# Dark green-black, darkest to lightest facet.
OBSIDIAN_SHADES = [rgba(c) for c in ("#081510", "#0d2016", "#132c1e", "#1b3d2a")]


def wrap_dist(a, b):
    d = abs(a - b) % 16
    return min(d, 16 - d)


def obsidian_facets(seed):
    """Tileable crystal facets: each pixel takes the shade of its nearest
    seed point (wrapping at the edges), with lighter facet borders."""
    rng = random.Random(seed)
    points = [(rng.uniform(0, 16), rng.uniform(0, 16), rng.randrange(len(OBSIDIAN_SHADES) - 1)) for _ in range(9)]
    grid = {}
    for y in range(16):
        for x in range(16):
            dists = sorted(
                (wrap_dist(x + 0.5, px) ** 2 + wrap_dist(y + 0.5, py) ** 2, shade) for px, py, shade in points)
            (d1, shade), (d2, _) = dists[0], dists[1]
            edge = d2 ** 0.5 - d1 ** 0.5 < 0.8
            grid[(x, y)] = OBSIDIAN_SHADES[min(shade + (1 if edge else 0), len(OBSIDIAN_SHADES) - 1)]
    return grid


def vein_path(seed, length):
    """A wandering, wrapping line of pixels for glowing veins."""
    rng = random.Random(seed)
    x, y = rng.randrange(16), rng.randrange(16)
    dx, dy = rng.choice(((1, 1), (1, -1), (-1, 1), (1, 0), (0, 1)))
    path = []
    for _ in range(length):
        if (x, y) not in path:
            path.append((x, y))
        if rng.random() < 0.35:
            dx, dy = rng.choice(((1, 1), (1, -1), (-1, 1), (1, 0), (0, 1), (-1, 0)))
        x, y = (x + dx) % 16, (y + dy) % 16
    return path


def obsidian_strip(frames=32):
    """Obsidian: dark green-black crystal with veins that a green pulse
    travels along. Tiles seamlessly."""
    facets = obsidian_facets("obsidian")
    veins = vein_path("obsidian-vein-a", 22) + vein_path("obsidian-vein-b", 14)
    strip = Image.new("RGBA", (16, 16 * frames))
    for f in range(frames):
        for (x, y), color in facets.items():
            strip.putpixel((x, y + 16 * f), color)
        for i, (x, y) in enumerate(veins):
            phase = (f / frames - i / len(veins)) % 1.0
            glow = max(0.0, math.cos(2 * math.pi * phase)) ** 6
            strip.putpixel((x, y + 16 * f), mix(GREEN["dark"], GREEN["glow"], 0.15 + 0.85 * glow))
    return strip


def crying_obsidian_strip(frames=32):
    """Crying obsidian: same crystal, but bright green tears run down it,
    so it never looks like plain obsidian."""
    facets = obsidian_facets("crying-obsidian")
    cracks = vein_path("crying-crack", 10)
    tears = [(2, 0, 1.0), (6, 5, 1.5), (10, 9, 1.0), (13, 3, 2.0)]  # column, start row, speed
    strip = Image.new("RGBA", (16, 16 * frames))
    for f in range(frames):
        for (x, y), color in facets.items():
            strip.putpixel((x, y + 16 * f), color)
        for x, y in cracks:
            strip.putpixel((x, y + 16 * f), GREEN["mid"])
        for col, start, speed in tears:
            head = (start + f * speed * 16 / frames) % 16
            for trail, tone in enumerate(("glow", "light", "mid")):
                y = int(head - trail) % 16
                strip.putpixel((col, y + 16 * f), GREEN[tone])
            strip.putpixel((col, start + 16 * f), GREEN["light"])  # the source of each tear
    return strip


# --------------------------------------------------------------------------
# End crystal
# --------------------------------------------------------------------------

END_GLASS = palette("#c8ffd8", "#7dea9a", "#3fae63", "#0e3a1c", shine="#ffffff")


def end_crystal_icon():
    """Item icon: a green glass frame around an emerald core, on an
    obsidian base."""
    sp = Sprite()
    cx, cy = 7.5, 6.0
    for y in range(16):
        for x in range(16):
            r = abs(x - cx) + abs(y - cy)
            if 5.0 <= r <= 6.0 and y <= 11:
                sp.put(x, y, END_GLASS["light" if y < cy else "mid"], END_GLASS)
            elif r <= 1.5:
                sp.put(x, y, GREEN["glow"], GREEN)
            elif r <= 3.0:
                sp.put(x, y, GREEN["light" if (x + y) % 2 else "mid"], GREEN)
    for x in range(3, 13):
        for y in (12, 13):
            sp.put(x, y, OBSIDIAN_SHADES[3 if y == 12 else 1], POMMEL)
    for x in (5, 7, 8, 10):
        sp.put(x, 12, GREEN["mid"], GREEN)
    return sp.outline()


def end_crystal_spin(frames=24):
    """The core throbs and a glint runs around the glass frame."""
    cx, cy = 7.5, 6.0

    def effect(f, x, y, color, pal):
        pulse = 0.5 - 0.5 * math.cos(2 * math.pi * f / frames)
        if pal is GREEN:
            return mix(color, (255, 255, 255, 255), 0.35 * pulse) if abs(x - cx) + abs(y - cy) <= 3 else color
        if pal is END_GLASS:
            angle = math.atan2(y - cy, x - cx) / (2 * math.pi) % 1.0
            dist = min(abs(angle - f / frames), 1 - abs(angle - f / frames))
            return mix(color, END_GLASS["shine"], max(0.0, 1 - dist * 8))
        return color

    return effect


def end_crystal_entity():
    """64x32 entity texture: outer glass cube (UV 0,0), core cube (UV 32,0)
    and base (UV 0,16)."""
    img = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    for name, (u, v, w, h) in cube_faces(0, 0, 8, 8, 8).items():  # glass: frame only
        for fy in range(h):
            for fx in range(w):
                edge = fx in (0, w - 1) or fy in (0, h - 1)
                corner = fx in (0, w - 1) and fy in (0, h - 1)
                if corner:
                    img.putpixel((u + fx, v + fy), END_GLASS["shine"])
                elif edge:
                    img.putpixel((u + fx, v + fy), END_GLASS["light"] if (fx + fy) % 2 else END_GLASS["mid"])
                elif (fx, fy) in ((2, 2), (3, 3), (5, 5)):
                    img.putpixel((u + fx, v + fy), END_GLASS["light"])
    for name, (u, v, w, h) in cube_faces(32, 0, 8, 8, 8).items():  # emerald core
        for fy in range(h):
            for fx in range(w):
                ring = max(abs(fx - 3.5), abs(fy - 3.5))
                tone = "glow" if ring <= 1 else ("light" if ring <= 2 else ("mid" if ring <= 3 else "dark"))
                img.putpixel((u + fx, v + fy), GREEN[tone])
    for name, (u, v, w, h) in cube_faces(0, 16, 12, 4, 12).items():  # obsidian base
        for fy in range(h):
            for fx in range(w):
                color = OBSIDIAN_SHADES[(fx * 7 + fy * 3) % 3 + 1]
                if name == "top" and (fx in (0, w - 1) or fy in (0, h - 1)):
                    color = GREEN["dark"]
                elif name in SIDES and fy == 1:
                    color = GREEN["light"] if fx % 3 else GREEN["glow"]
                img.putpixel((u + fx, v + fy), color)
    return img

# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def save(img, root: Path, rel: str):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def build(root: Path) -> dict[str, Image.Image]:
    """Writes the pack under root and returns the item images for previews."""
    items: dict[str, Image.Image] = {}
    item_dir = "assets/minecraft/textures/item/"

    def item(name, img):
        items[name] = img
        save(img, root, f"{item_dir}{name}.png")

    def animated(name, strip, folder=item_dir):
        """Saves an animated texture; previews get the first frame and the strip."""
        items[name] = strip.crop((0, 0, 16, 16))
        items[f"anim:{name}"] = strip
        save(strip, root, f"{folder}{name}.png")
        meta = {"animation": {"frametime": FRAME_TIME, "interpolate": True}}
        (root / f"{folder}{name}.png.mcmeta").write_text(json.dumps(meta, indent=2) + "\n")

    glint = weapon_glint()
    for material, pal in TOOL.items():
        animated(f"{material}_sword", render_strip(sword(pal), 24, glint))
        animated(f"{material}_axe", render_strip(axe(pal), 24, glint))
    animated("mace", render_strip(mace(), 24, glint))
    animated("trident", trident_storm(trident()))
    animated("bow", render_strip(bow(None), 24, glint))
    for i in range(3):
        animated(f"bow_pulling_{i}", render_strip(bow(i), 24, glint))
    for state in ("standby", "pulling_0", "pulling_1", "pulling_2", "arrow", "firework"):
        animated(f"crossbow_{state}", render_strip(crossbow(state), 24, glint))
    item("arrow", arrow().image())
    animated("totem_of_undying", render_strip(totem(), 24, totem_aura()))
    animated("elytra", render_strip(elytra_icon(), 24, glint))
    item("broken_elytra", broken_elytra_icon())
    animated("end_crystal", render_strip(end_crystal_icon(), 24, end_crystal_spin()))
    item("golden_apple", from_ascii(GOLDEN_APPLE_ROWS, TOOL["golden"]).image())
    item("ender_pearl", from_ascii(ENDER_PEARL_ROWS, PEARL).image())

    for material, (worn, pal) in ARMOR.items():
        for piece, rows in ARMOR_ICONS.items():
            name = f"{material}_{piece}"
            if material == "leather":
                base, overlay = leather_icon(rows)
                item(name, base)  # dye-tinted, so it stays still; the green overlay animates
                animated(f"{name}_overlay", render_strip(overlay, 24, glint))
            else:
                animated(name, render_strip(armor_icon(rows, pal, chainmail=material == "chainmail"), 24, glint))

        if material == "leather":
            l1, l2 = armor_layers(material, pal, no_green=True)
            o1, o2 = armor_layers(material, pal, only_green=True)
        else:
            l1, l2 = armor_layers(material, pal)
            o1 = o2 = None
        # 1.21.1 and earlier
        save(l1, root, f"assets/minecraft/textures/models/armor/{worn}_layer_1.png")
        save(l2, root, f"assets/minecraft/textures/models/armor/{worn}_layer_2.png")
        # 1.21.2 and later
        save(l1, root, f"assets/minecraft/textures/entity/equipment/humanoid/{worn}.png")
        save(l2, root, f"assets/minecraft/textures/entity/equipment/humanoid_leggings/{worn}.png")
        if o1 is not None:
            save(o1, root, f"assets/minecraft/textures/models/armor/{worn}_layer_1_overlay.png")
            save(o2, root, f"assets/minecraft/textures/models/armor/{worn}_layer_2_overlay.png")
            save(o1, root, f"assets/minecraft/textures/entity/equipment/humanoid/{worn}_overlay.png")
            save(o2, root, f"assets/minecraft/textures/entity/equipment/humanoid_leggings/{worn}_overlay.png")
        items[f"worn:{material}"] = (l1, l2, o1, o2)

    save(shield(), root, "assets/minecraft/textures/entity/shield_base_nopattern.png")

    wings = elytra_entity()
    save(wings, root, "assets/minecraft/textures/entity/elytra.png")  # 1.21.1
    save(wings, root, "assets/minecraft/textures/entity/equipment/wings/elytra.png")  # 1.21.2+
    items["entity:elytra"] = wings
    crystal = end_crystal_entity()
    save(crystal, root, "assets/minecraft/textures/entity/end_crystal/end_crystal.png")
    items["entity:end_crystal"] = crystal

    block_dir = "assets/minecraft/textures/block/"
    animated("obsidian", obsidian_strip(), block_dir)
    animated("crying_obsidian", crying_obsidian_strip(), block_dir)

    icon = items["iron_sword"].resize((64, 64), Image.NEAREST)  # first frame
    save(icon, root, "pack.png")
    mcmeta = {
        "pack": {
            "pack_format": 34,
            "supported_formats": {"min_inclusive": 34, "max_inclusive": 64},
            "description": "Green PvP: vine-forged weapons & armor",
        }
    }
    (root / "pack.mcmeta").write_text(json.dumps(mcmeta, indent=2) + "\n")
    return items


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "pack")
    build(out)
    print(f"Wrote pack to {out}")
