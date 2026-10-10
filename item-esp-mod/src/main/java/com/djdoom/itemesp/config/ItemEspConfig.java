package com.djdoom.itemesp.config;

import com.djdoom.itemesp.ItemEspClient;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonParseException;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.item.Item;

import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.LinkedHashSet;
import java.util.Set;

/**
 * User settings, persisted as JSON in {@code config/itemesp.json}.
 *
 * <p>Every item in the game is tracked by default; the filter stores the
 * items the user has switched off so newly added items (from game updates
 * or other mods) are tracked automatically.
 */
public final class ItemEspConfig {
    public static final int MIN_CHUNK_RADIUS = 1;
    public static final int MAX_CHUNK_RADIUS = 32;
    public static final int MIN_MAX_ITEMS = 16;
    public static final int MAX_MAX_ITEMS = 2048;
    public static final int MAX_MIN_COUNT = 64;

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final Path FILE = FabricLoader.getInstance().getConfigDir().resolve("itemesp.json");

    public boolean enabled = true;
    public boolean tracers = true;
    public boolean boxes = true;
    public boolean labels = true;
    public boolean hud = true;
    public boolean throughWalls = true;
    public boolean showScanArea = false;
    public ColorMode colorMode = ColorMode.ITEM;
    public int chunkRadius = 4;
    public int maxItems = 256;
    public int minCount = 1;
    public float lineWidth = 2.0f;
    public int fixedHue = 120;
    public int hudLines = 8;
    public Set<String> ignoredItems = new LinkedHashSet<>();

    public static ItemEspConfig load() {
        if (Files.isRegularFile(FILE)) {
            try (Reader reader = Files.newBufferedReader(FILE)) {
                ItemEspConfig config = GSON.fromJson(reader, ItemEspConfig.class);
                if (config != null) {
                    config.sanitize();
                    return config;
                }
            } catch (IOException | JsonParseException e) {
                ItemEspClient.LOGGER.warn("Could not read {}, using defaults", FILE, e);
            }
        }
        ItemEspConfig config = new ItemEspConfig();
        config.save();
        return config;
    }

    public void save() {
        sanitize();
        try {
            Files.createDirectories(FILE.getParent());
            // Write to a temp file first so a crash mid-write can't corrupt the config.
            Path temp = FILE.resolveSibling(FILE.getFileName() + ".tmp");
            try (Writer writer = Files.newBufferedWriter(temp)) {
                GSON.toJson(this, writer);
            }
            Files.move(temp, FILE, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            ItemEspClient.LOGGER.error("Could not save {}", FILE, e);
        }
    }

    public void resetToDefaults() {
        ItemEspConfig defaults = new ItemEspConfig();
        enabled = defaults.enabled;
        tracers = defaults.tracers;
        boxes = defaults.boxes;
        labels = defaults.labels;
        hud = defaults.hud;
        throughWalls = defaults.throughWalls;
        showScanArea = defaults.showScanArea;
        colorMode = defaults.colorMode;
        chunkRadius = defaults.chunkRadius;
        maxItems = defaults.maxItems;
        minCount = defaults.minCount;
        lineWidth = defaults.lineWidth;
        fixedHue = defaults.fixedHue;
        hudLines = defaults.hudLines;
        ignoredItems.clear();
    }

    public boolean isTracked(Item item) {
        return !ignoredItems.contains(itemId(item));
    }

    public void setTracked(Item item, boolean tracked) {
        String id = itemId(item);
        if (tracked) {
            ignoredItems.remove(id);
        } else {
            ignoredItems.add(id);
        }
    }

    public static String itemId(Item item) {
        return BuiltInRegistries.ITEM.getKey(item).toString();
    }

    /** Clamps values from hand-edited or older config files into valid ranges. */
    private void sanitize() {
        chunkRadius = clamp(chunkRadius, MIN_CHUNK_RADIUS, MAX_CHUNK_RADIUS);
        maxItems = clamp(maxItems, MIN_MAX_ITEMS, MAX_MAX_ITEMS);
        minCount = clamp(minCount, 1, MAX_MIN_COUNT);
        fixedHue = Math.floorMod(fixedHue, 360);
        hudLines = clamp(hudLines, 0, 20);
        lineWidth = Math.max(1.0f, Math.min(5.0f, lineWidth));
        if (colorMode == null) {
            colorMode = ColorMode.ITEM;
        }
        if (ignoredItems == null) {
            ignoredItems = new LinkedHashSet<>();
        }
    }

    private static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }
}
