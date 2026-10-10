package com.djdoom.itemesp.tracker;

import com.djdoom.itemesp.config.ItemEspConfig;
import net.minecraft.world.item.ItemStack;

import java.awt.Color;

/** Picks the RGB color for a tracked item based on the configured color mode. */
public final class EspColors {
    private EspColors() {
    }

    public static int colorFor(ItemStack stack, double distance, double maxDistance, ItemEspConfig config) {
        return switch (config.colorMode) {
            case ITEM -> {
                // Golden-ratio hue spacing keeps similar ids from getting similar colors.
                int hash = ItemEspConfig.itemId(stack.getItem()).hashCode();
                float hue = (float) ((hash * 0.6180339887) % 1.0 + 1.0) % 1.0f;
                yield hsv(hue, 0.75f, 1.0f);
            }
            case DISTANCE -> {
                // Red when close, through yellow, to green at the edge of the scan area.
                float t = maxDistance <= 0 ? 0f : (float) Math.max(0.0, Math.min(1.0, distance / maxDistance));
                yield hsv(t / 3f, 1f, 1f);
            }
            case FIXED -> hsv(config.fixedHue / 360f, 1f, 1f);
        };
    }

    /** Converts an RGB color plus alpha (0-255) into ARGB. */
    public static int withAlpha(int rgb, int alpha) {
        return (alpha & 0xFF) << 24 | (rgb & 0xFFFFFF);
    }

    private static int hsv(float hue, float saturation, float value) {
        return Color.HSBtoRGB(hue, saturation, value) & 0xFFFFFF;
    }
}
