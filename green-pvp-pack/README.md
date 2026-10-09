# Green PvP resource pack (+ Green Everything)

Vine-forged, green-themed textures for PvP gear, designed to pair with
[Green Shaders](../green-shaders/). There are two ways to use it:

| Pack | What's green | How to get it |
| --- | --- | --- |
| **GreenPvP.zip** | The hand-made textures listed below | Ready to use: `dist/GreenPvP.zip` |
| **GreenEverything.zip** | Every item, block, particle and mob in the game, plus everything in GreenPvP | Build it on your computer from your own game files with `greenify` (see below) |

 Swords follow the reference design: a blade in the
material's own color with a dark fuller, a dark wrapped handle, and a green vine
crossguard and pommel set with an emerald.

![All textures](preview.png)

![Animations](preview-animations.gif)

## What's included

| Group | Items |
| --- | --- |
| Swords and axes | wooden, stone, iron, golden, diamond, netherite |
| Other weapons | mace, trident (inventory icon), bow (+3 pull stages), crossbow (standby, 3 pull stages, loaded arrow, loaded firework), arrow, shield |
| Totem | totem of undying drawn from the player skin: crown with gems, green face, black suit, red tie, green hands |
| Consumables | golden apple (the enchanted one uses the same texture), ender pearl |
| Elytra | item icon, broken elytra (torn and faded, so you notice), and the wings when flying |
| End crystal (special) | animated item icon and the placed crystal: green glass frame, glowing emerald core, obsidian-green base |
| Obsidian (special) | animated green-black crystal with glowing veins; crying obsidian with green tears running down |
| Armor icons | leather (dyeable, green parts stay green), chainmail, iron, golden, diamond, netherite |
| Worn armor | all six materials, for both 1.21.1 and 1.21.2+ texture paths |

## Animations

All animations use the game's built-in animated textures (`.png.mcmeta`), so they work
without mods or OptiFine.

- **Swords, axes, mace, bow and crossbow:** a green glint sweeps from the handle to the
  tip, then the emeralds and vines pulse until the next sweep (2.4 second loop). The
  glint only covers a narrow band, so the material color shows most of the time.
- **Trident (special):** a bolt of green energy climbs the shaft, the prongs flash,
  sparks crackle around the tips, and then it settles into a soft glow (3.2 second loop).
- **Armor and elytra icons:** the same green glint as the weapons. Leather armor animates
  its green overlay, so dyes still work.
- **Totem:** its outline breathes green, and the four crown gems twinkle in turn. The
  animation also plays in the totem pop when it saves you.
- **End crystal:** the emerald core throbs and a glint circles the glass frame.
- **Obsidian:** pulses of green light travel along its veins. **Crying obsidian:** green
  tears run down it.

Animated textures show in the inventory, in your hand, on dropped items and (for obsidian)
on placed blocks. Worn armor, the elytra wings, the placed end crystal and the 3D trident
use entity textures, which the game can't animate, so those are drawn green but stay still.
The placed end crystal already spins and bobs on its own.

## Green Everything

`greenify.py` makes every texture in the game green, then puts the hand-made textures on
top. Mojang's textures can't be shared, so it runs on your computer and reads them from
your own copy of the game.

1. Unzip `dist/GreenEverything-builder.zip` anywhere (it holds `greenify.py`, the
   launchers and the hand-made textures).
2. Launch Minecraft 1.21.1 once with the official launcher, so the game files exist.
3. Install [Python 3](https://www.python.org/downloads/). On Windows, tick
   **Add Python to PATH**.
4. Run it from the unzipped folder:
   - **Windows:** double-click `greenify.bat`
   - **macOS/Linux:** `./greenify.sh`
   - Other versions: `greenify.bat --version 1.21.4` (or `./greenify.sh --version 1.21.4`)
5. Put the `dist/GreenEverything.zip` it creates (inside the unzipped folder) into
   `.minecraft/resourcepacks/`, and use it **instead of** GreenPvP.zip.

How it keeps things tellable apart: colors are squeezed toward green, not painted over.
Red becomes yellow-green, blue becomes teal, grays get a green tint, and brightness never
changes, so a diamond ore still looks different from an emerald ore. It leaves alone:

- potions, tipped arrows, spawn eggs, banners and armor trim colors (their color is information)
- dyed leather, and grass, leaves, water and redstone dust (the game colors these itself)
- player skins and capes

How strongly each kind of texture turns green is set in `LEAN` at the top of `greenify.py`.

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

## Not covered by GreenPvP.zip

- In GreenPvP.zip, the thrown or held 3D trident, the turtle helmet and tools other than
  axes keep their vanilla look. GreenEverything.zip makes all of those green too.
