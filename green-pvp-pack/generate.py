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

Usage: python3 generate.py [output_dir]   (default: ./pack)
Requires Pillow.
"""

from __future__ import annotations

import colorsys
import json
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
TOTEM = palette("#ffe98a", "#e2b33a", "#9c6f17", "#4a3005", shine="#fff7d1")
PEARL = palette("#b8f0d0", "#3aa071", "#0f4a3a", "#062019", shine="#ffffff")
SHIELD_WOOD = palette("#8a6034", "#6d4a26", "#4f3519", "#24170a")

# --------------------------------------------------------------------------
# Sprite helpers
# --------------------------------------------------------------------------


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
            if pal is None:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if 0 <= n[0] < self.w and 0 <= n[1] < self.h and n not in self.px and n not in added:
                    added[n] = (pal["outline"], None)
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

TOTEM_ROWS = [
    "................",
    ".....oooooo.....",
    "....oLLLLLMo....",
    "....oLeLLeMo....",
    "....oLLLLLMo....",
    "....oMoDDoMo....",
    "..ooooMMMMoooo..",
    ".oLLLLGEEGLLLMo.",
    ".oMMoLGeeGMoDDo.",
    "..oo.oLMMMo.oo..",
    ".....oLGGMo.....",
    ".....oLMMMo.....",
    ".....oLMMMo.....",
    ".....oMooMo.....",
    ".....oo..oo.....",
    "................",
]

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
    return sp.image()


def leather_icon(rows):
    """Leather is dye-tinted, so green goes in the untinted overlay."""
    pal = ARMOR["leather"][1]
    base_rows = ["".join("M" if c in GREEN_CODES - {"k"} else ("o" if c == "k" else c) for c in r) for r in rows]
    overlay_rows = ["".join(c if c in GREEN_CODES else "." for c in r) for r in rows]
    return from_ascii(base_rows, pal).image(), from_ascii(overlay_rows, pal).image()


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

    for material, pal in TOOL.items():
        item(f"{material}_sword", sword(pal).image())
        item(f"{material}_axe", axe(pal).image())
    item("mace", mace().image())
    item("trident", trident().image())
    item("bow", bow(None).image())
    for i in range(3):
        item(f"bow_pulling_{i}", bow(i).image())
    for state in ("standby", "pulling_0", "pulling_1", "pulling_2", "arrow", "firework"):
        item(f"crossbow_{state}", crossbow(state).image())
    item("arrow", arrow().image())
    item("totem_of_undying", from_ascii(TOTEM_ROWS, TOTEM).image())
    item("golden_apple", from_ascii(GOLDEN_APPLE_ROWS, TOOL["golden"]).image())
    item("ender_pearl", from_ascii(ENDER_PEARL_ROWS, PEARL).image())

    for material, (worn, pal) in ARMOR.items():
        for piece, rows in ARMOR_ICONS.items():
            name = f"{material}_{piece}"
            if material == "leather":
                base, overlay = leather_icon(rows)
                item(name, base)
                save(overlay, root, f"{item_dir}{name}_overlay.png")
                items[f"{name}_overlay"] = overlay
            else:
                item(name, armor_icon(rows, pal, chainmail=material == "chainmail"))

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

    icon = items["iron_sword"].resize((64, 64), Image.NEAREST)
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
