# Green PvP resource pack

Vine-forged, green-themed textures for PvP gear, designed to pair with
[Green Shaders](../green-shaders/). Swords follow the reference design: a blade in the
material's own color with a dark fuller, a dark wrapped handle, and a green vine
crossguard and pommel set with an emerald.

![All textures](preview.png)

## What's included

| Group | Items |
| --- | --- |
| Swords and axes | wooden, stone, iron, golden, diamond, netherite |
| Other weapons | mace, trident (inventory icon), bow (+3 pull stages), crossbow (standby, 3 pull stages, loaded arrow, loaded firework), arrow, shield |
| Consumables | totem of undying, golden apple (the enchanted one uses the same texture), ender pearl |
| Armor icons | leather (dyeable, green parts stay green), chainmail, iron, golden, diamond, netherite |
| Worn armor | all six materials, for both 1.21.1 and 1.21.2+ texture paths |

## Telling gear apart

- **Weapons** keep each material's hue on the blade or head: wood is brown, stone gray,
  iron near-white, gold yellow, diamond aqua and netherite near-black. Green only appears
  on the guard, pommel, bindings and vines.
- **Armor** is pulled toward green (`ARMOR_GREEN_LEAN` in `generate.py`) without changing
  its lightness. Iron stays the lightest and netherite the darkest; gold still reads as
  yellow, diamond as aqua, and chainmail keeps its mesh pattern.
- **Leather armor** is still dyeable. The vines live in the overlay texture, so they
  stay green whatever dye you use.
- **Potions and tipped arrows are untouched**, because their colors tell you the effect.
- With the shader, turn on **Protect PvP Colors** (on by default) so the green grade
  doesn't wash out these colors.

## Install

1. Use `dist/GreenPvP.zip` (build it with `./build.sh`, which needs Python 3 and Pillow),
   or zip the *contents* of `pack/` so that `pack.mcmeta` sits at the root of the zip.
2. Put the zip in `.minecraft/resourcepacks/` and enable it under
   **Options → Resource Packs**.

The pack targets Minecraft 1.21.1 (pack format 34) and declares support up to format 64.
On newer versions the game marks it "made for an older version", but it still loads
when you confirm.

## Customizing

Every texture is drawn in code in `generate.py`; no Mojang textures are copied.
Change palettes (`TOOL`, `ARMOR`, `GREEN`), the armor green lean, or shapes, then run
`./build.sh`. `preview.py` renders `preview.png`, which shows every icon plus a front view
of each worn armor set.

## Not covered

- The held trident and the shield use 3D models. The shield texture is replaced, but the
  thrown or held trident keeps its vanilla model texture.
- Turtle helmet, elytra and tools other than axes are unchanged.
