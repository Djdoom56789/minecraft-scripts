package com.djdoom.itemesp.config;

import net.minecraft.network.chat.Component;

/** How ESP outlines, tracers and labels are colored. */
public enum ColorMode {
    /** Every item type gets its own stable color, so different items are easy to tell apart. */
    ITEM("item"),
    /** Fades from red (close) to green (edge of the scan radius). */
    DISTANCE("distance"),
    /** A single user-chosen hue. */
    FIXED("fixed");

    private final String key;

    ColorMode(String key) {
        this.key = key;
    }

    public Component displayName() {
        return Component.translatable("itemesp.option.color_mode." + key);
    }

    public ColorMode next() {
        ColorMode[] values = values();
        return values[(ordinal() + 1) % values.length];
    }
}
