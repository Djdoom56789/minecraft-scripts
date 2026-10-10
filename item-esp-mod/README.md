# Item ESP (Fabric, Minecraft 26.3)

A client-side Fabric mod that highlights every dropped item in the game within an
adjustable radius of chunks around you. **It only runs in single-player worlds**; on
servers or LAN-shared worlds it switches itself off.

Built for **Minecraft 26.3, Fabric Loader 0.19.5 and Fabric API 0.162.0+26.3**. The
1.21.1 version lives in [`../item-esp-mod-1.21.1`](../item-esp-mod-1.21.1/).

## Features

- **Every item tracked by default**: vanilla and modded. The item filter lists every
  registered item, with a search box and per-item on/off buttons.
- **Tracers** from your crosshair to each item, **boxes** around them, and floating
  **labels** (`Diamond x5 · 12m`).
- **Chunk radius**, 1–32 chunks: a square of chunks centered on yours, the same shape as
  render distance. It's limited to your render distance, because the game only loads
  items that far out (the menu warns you when it's above that).
- **HUD list** of the nearest items, with a color swatch matching each item's box.
- **Color modes**: by item (every item type gets its own color), by distance (red is near,
  green is far), or one fixed hue.
- Line width, max tracked items, minimum stack size, see-through labels, and an optional
  outline of the scanned area.

## Controls

| Key | Action |
| --- | --- |
| `U` | Open the settings menu |
| `Y` | Toggle the ESP on/off |
| `]` / `[` | Increase / decrease the chunk radius |

Rebind them under **Options → Controls → Key Binds → Item ESP**. Settings are saved to
`.minecraft/config/itemesp.json`.

## Building the .jar

Requires **JDK 25** and internet access (Gradle downloads Minecraft and Fabric).

```sh
./gradlew build          # Windows: gradlew.bat build
```

The mod jar is `build/libs/item-esp-2.0.0.jar` (ignore the `-sources` jar). Put it in
`.minecraft/mods/` together with [Fabric API](https://modrinth.com/mod/fabric-api) for
26.3.

## How it was ported, and what to expect

Minecraft 26.x renamed and reworked most of the client code: Mojang's own names instead
of Yarn, SDL keyboard codes, and a new "extract then submit" rendering system. This version
uses only APIs that Fabric API's own 26.3 code and test mods use: `LevelRenderEvents`,
`submitCustomGeometry` with `RenderTypes.debugFilledBox()`, `submitNameTag`,
`HudElementRegistry`, `KeyMappingHelper`, `Button.builder`, `EditBox` and
`GuiGraphicsExtractor`. To stay on that confirmed ground:

- The settings menu uses on/off buttons and − / + buttons instead of sliders, and the
  item filter is pages of buttons instead of a scrolling list with item icons.
- Lines are drawn as thin camera-facing ribbons, using the same filled-box render type as
  Fabric's render test.
- Boxes and tracers follow that render type's depth rules, so they may be hidden behind
  blocks. Labels can always show through walls (the **Labels Through Walls** setting).

It couldn't be compiled where it was written, because the build machine had no access to
Fabric's or Mojang's download servers. If `./gradlew build` reports an error, the error
output names the exact file and line to fix.

## Code layout

| Package | Responsibility |
| --- | --- |
| `ItemEspClient` | Entrypoint: key mappings, tick loop, single-player guard |
| `config` | Settings model with JSON persistence and validation |
| `tracker` | Once-per-tick scan of item entities in the chunk square, sorted by distance |
| `render` | World-space boxes, tracers and labels; HUD panel |
| `gui` | Settings screen and the searchable per-item filter |
