package com.djdoom.itemesp.config;

import net.minecraft.text.Text;

/** How ESP outlines, tracers and labels are colored. */
public enum ColorMode {
    /** Uses the item's rarity color (white, yellow, aqua, light purple). */
    RARITY("rarity"),
    /** Fades from red (close) to green (edge of the scan radius). */
    DISTANCE("distance"),
    /** A single user-chosen hue. */
    FIXED("fixed");

    private final String key;

    ColorMode(String key) {
        this.key = key;
    }

    public Text displayName() {
        return Text.translatable("itemesp.option.color_mode." + key);
    }
}
