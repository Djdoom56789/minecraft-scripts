#!/usr/bin/env python3
"""Renders preview.png: every item icon plus a front view of each armor set."""

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

import generate

SCALE = 4
CELL = 16 * SCALE + 12
BACKGROUND = (44, 47, 51, 255)
MANNEQUIN = (120, 124, 128, 255)


def tint(img, rgb):
    color = Image.new("RGBA", img.size, rgb + (255,))
    tinted = ImageChops.multiply(img, color)
    tinted.putalpha(img.getchannel("A"))
    return tinted


def front_view(layer1, layer2, overlay1=None, overlay2=None, tint_rgb=None):
    """Composites the front faces of the armor layers onto a 16x32 figure."""
    view = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(view)
    draw.rectangle((4, 0, 11, 7), fill=MANNEQUIN)
    draw.rectangle((0, 8, 15, 19), fill=MANNEQUIN)
    draw.rectangle((4, 20, 11, 31), fill=MANNEQUIN)

    def faces(layer):
        return {
            "head": layer.crop((8, 8, 16, 16)),
            "body": layer.crop((20, 20, 28, 32)),
            "arm": layer.crop((44, 20, 48, 32)),
            "leg": layer.crop((4, 20, 8, 32)),
        }

    def place(layer, legs_only=False):
        f = faces(layer)
        if not legs_only:
            view.alpha_composite(f["head"], (4, 0))
            view.alpha_composite(f["arm"], (0, 8))
            view.alpha_composite(f["arm"].transpose(Image.FLIP_LEFT_RIGHT), (12, 8))
        view.alpha_composite(f["body"], (4, 8))
        view.alpha_composite(f["leg"], (4, 20))
        view.alpha_composite(f["leg"].transpose(Image.FLIP_LEFT_RIGHT), (8, 20))

    if tint_rgb:
        layer1, layer2 = tint(layer1, tint_rgb), tint(layer2, tint_rgb)
    place(layer2, legs_only=True)
    if overlay2:
        place(overlay2, legs_only=True)
    place(layer1)
    if overlay1:
        place(overlay1)
    return view


def main(out_path):
    items = generate.build(Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / "pack")
    rows = [
        [f"{m}_sword" for m in generate.TOOL],
        [f"{m}_axe" for m in generate.TOOL],
        ["mace", "trident", "bow", "bow_pulling_2", "crossbow_standby", "crossbow_arrow"],
        ["arrow", "totem_of_undying", "golden_apple", "ender_pearl", "crossbow_firework", "bow_pulling_0"],
    ]
    for piece in generate.ARMOR_ICONS:
        rows.append([f"{m}_{piece}" for m in generate.ARMOR])

    figure_scale = 3
    fig_w, fig_h = 16 * figure_scale + 12, 32 * figure_scale + 12
    width = max(len(r) for r in rows) * CELL + 12
    height = len(rows) * CELL + fig_h + 24
    sheet = Image.new("RGBA", (width, height), BACKGROUND)

    for r, names in enumerate(rows):
        for c, name in enumerate(names):
            icon = items[name]
            if name.startswith("leather_"):
                icon = tint(icon, generate.LEATHER_DEFAULT_TINT)
                icon.alpha_composite(items[f"{name}_overlay"])
            sheet.alpha_composite(icon.resize((16 * SCALE, 16 * SCALE), Image.NEAREST), (12 + c * CELL, 12 + r * CELL))

    y = 12 + len(rows) * CELL + 6
    for c, material in enumerate(generate.ARMOR):
        l1, l2, o1, o2 = items[f"worn:{material}"]
        view = front_view(l1, l2, o1, o2, generate.LEATHER_DEFAULT_TINT if material == "leather" else None)
        sheet.alpha_composite(view.resize((16 * figure_scale, 32 * figure_scale), Image.NEAREST),
                              (12 + c * CELL + (CELL - fig_w) // 2, y))
    sheet.save(out_path)
    print(f"Wrote {out_path}")
    animation_gif(items, str(Path(out_path).with_name("preview-animations.gif")))


def animation_gif(items, out_path):
    """Loops every animated texture together (without the game's frame interpolation)."""
    names = [k[len("anim:"):] for k in items if k.startswith("anim:")]
    order = ["totem_of_undying", "trident"] + [n for n in names if n.endswith("_sword")] + \
            [n for n in names if n.endswith("_axe")] + ["mace", "bow", "bow_pulling_2", "crossbow_arrow"]
    names = [n for n in order if f"anim:{n}" in items]
    strips = {n: items[f"anim:{n}"] for n in names}
    counts = {n: s.height // 16 for n, s in strips.items()}
    total = 1
    for c in counts.values():
        total = total * c // __import__("math").gcd(total, c)
    scale, cols = 5, 6
    cell = 16 * scale + 8
    rows = (len(names) + cols - 1) // cols
    frames = []
    for f in range(total):
        frame = Image.new("RGBA", (cols * cell, rows * cell), BACKGROUND)
        for i, n in enumerate(names):
            k = f % counts[n]
            sprite = strips[n].crop((0, 16 * k, 16, 16 * k + 16)).resize((16 * scale, 16 * scale), Image.NEAREST)
            frame.alpha_composite(sprite, ((i % cols) * cell + 4, (i // cols) * cell + 4))
        frames.append(frame.convert("RGB"))
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=100, loop=0)
    print(f"Wrote {out_path} ({total} frames)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent / "preview.png"))
