# Item ESP (Fabric, Minecraft 1.21.1)

A client-side Fabric mod that highlights every dropped item in the game within an
adjustable radius of chunks around you. **It only runs in single-player worlds**; on
servers or LAN-shared worlds it switches itself off.

## Features

- **Every item tracked by default**: vanilla and modded. The item filter lists every
  registered item with a search box and per-item on/off toggles.
- **Tracers** from your crosshair to each item, **boxes** around them, and floating
  **labels** (`Diamond x5 · 12m`) that scale up with distance so they stay readable.
- **Chunk radius**, 1–32 chunks: a square of chunks centered on yours, the same shape as
  render distance. It's limited to your render distance, because the game only loads
  items that far out (the menu warns when your setting is above it).
- **HUD list** of the nearest items with icons, counts and distances.
- **Color modes**: by rarity, by distance (red is near, green is far), or one fixed hue.
- Through-walls toggle, line width, max tracked items, minimum stack size, and an
  optional outline of the scanned area.

## Controls

| Key | Action |
| --- | --- |
| `U` | Open the settings menu |
| `Y` | Toggle the ESP on/off |
| `]` / `[` | Increase / decrease the chunk radius |

All keys can be rebound under **Options → Controls → Key Binds → Item ESP**.
Settings are saved to `.minecraft/config/itemesp.json`.

## Building the .jar

Requires JDK 21 and internet access (Gradle downloads Minecraft and Fabric).

```sh
./gradlew build          # Windows: gradlew.bat build
```

The mod jar is `build/libs/item-esp-1.0.0.jar` (ignore the `-sources` jar).
Run `./gradlew runClient` to launch a development client with the mod loaded.

## Installing

1. Install [Fabric Loader](https://fabricmc.net/use/) for Minecraft 1.21.1.
2. Put `item-esp-1.0.0.jar` and [Fabric API](https://modrinth.com/mod/fabric-api) for
   1.21.1 in `.minecraft/mods/`.
3. Launch the Fabric profile and open a single-player world.

## Targeting another Minecraft version

The versions are in `gradle.properties`. Get matching values from
<https://fabricmc.net/develop>. The rendering code uses 1.21.1 APIs
(`RenderSystem.applyModelViewMatrix`, `getPositionColorProgram`), which changed in
1.21.2 and later, so other versions also need small changes in `EspRenderer`.

## Code layout

| Package | Responsibility |
| --- | --- |
| `ItemEspClient` | Entrypoint: key bindings, tick loop, single-player guard |
| `config` | Settings model with JSON persistence and validation |
| `tracker` | Once-per-tick scan of item entities in the chunk square, sorted by distance |
| `render` | World-space boxes, tracers and labels; HUD panel |
| `gui` | Settings screen, sliders, and the searchable per-item filter screen |

The scan runs once per tick (20/s) and rendering reads that snapshot, so the per-frame
cost doesn't grow with the number of loaded entities. Labels are capped at the nearest
64 items, because text costs far more to draw than lines.

## Known limitations

- Line width above 1 may be ignored on macOS (core-profile OpenGL limitation).
- With view bobbing on, tracers start slightly off the crosshair while walking.
