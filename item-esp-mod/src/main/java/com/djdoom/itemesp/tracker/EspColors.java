package com.djdoom.itemesp.tracker;

import com.djdoom.itemesp.config.ItemEspConfig;
import net.minecraft.item.ItemStack;
import net.minecraft.util.math.MathHelper;

/** Picks the RGB color for a tracked item based on the configured color mode. */
public final class EspColors {
    private static final int WHITE = 0xFFFFFF;

    private EspColors() {
    }

    public static int colorFor(ItemStack stack, double distance, double maxDistance, ItemEspConfig config) {
        return switch (config.colorMode) {
            case RARITY -> {
                Integer rgb = stack.getRarity().getFormatting().getColorValue();
                yield rgb != null ? rgb : WHITE;
            }
            case DISTANCE -> {
                // Red when close, through yellow, to green at the edge of the scan area.
                float t = maxDistance <= 0 ? 0f : (float) MathHelper.clamp(distance / maxDistance, 0.0, 1.0);
                yield MathHelper.hsvToRgb(t / 3f, 1f, 1f) & 0xFFFFFF;
            }
            case FIXED -> MathHelper.hsvToRgb(config.fixedHue / 360f, 1f, 1f) & 0xFFFFFF;
        };
    }

    /** Converts an RGB color plus alpha (0-255) into ARGB. */
    public static int withAlpha(int rgb, int alpha) {
        return (alpha & 0xFF) << 24 | (rgb & 0xFFFFFF);
    }
}
