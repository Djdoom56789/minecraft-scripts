package com.djdoom.itemesp.render;

import com.djdoom.itemesp.ItemEspClient;
import com.djdoom.itemesp.config.ItemEspConfig;
import com.djdoom.itemesp.tracker.EspColors;
import com.djdoom.itemesp.tracker.ItemTracker;
import com.djdoom.itemesp.tracker.TrackedItem;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.world.item.ItemStack;

import java.util.List;
import java.util.function.Supplier;

/** Corner panel listing the nearest tracked items. */
public final class HudOverlay {
    private static final int MARGIN = 4;
    private static final int PADDING = 3;
    private static final int ROW_HEIGHT = 11;
    private static final int SWATCH = 7;
    private static final int PANEL_COLOR = 0x90000000;
    private static final int HEADER_COLOR = 0xFF55FF55;
    private static final int MUTED_COLOR = 0xFFAAAAAA;

    private final Supplier<ItemEspConfig> config;
    private final ItemTracker tracker;

    public HudOverlay(Supplier<ItemEspConfig> config, ItemTracker tracker) {
        this.config = config;
        this.tracker = tracker;
    }

    /** "Diamond x5 · 12m": shared by the HUD and the in-world labels. */
    public static MutableComponent describe(ItemStack stack, double distance) {
        MutableComponent text = stack.getHoverName().copy();
        if (stack.getCount() > 1) {
            text.append(" x" + stack.getCount());
        }
        return text.append(" · " + Math.round(distance) + "m");
    }

    public void extractRenderState(GuiGraphicsExtractor graphics, DeltaTracker deltaTracker) {
        Minecraft client = Minecraft.getInstance();
        ItemEspConfig cfg = config.get();
        if (!cfg.enabled || !cfg.hud || client.player == null) {
            return;
        }
        Font font = client.font;

        if (!ItemEspClient.isAllowed(client)) {
            String warning = Component.translatable("itemesp.hud.singleplayer_only").getString();
            graphics.fill(MARGIN, MARGIN, MARGIN + font.width(warning) + PADDING * 2,
                    MARGIN + font.lineHeight + PADDING * 2, PANEL_COLOR);
            graphics.text(font, warning, MARGIN + PADDING, MARGIN + PADDING, MUTED_COLOR);
            return;
        }

        List<TrackedItem> items = tracker.items();
        int shown = Math.min(items.size(), cfg.hudLines);
        int hidden = tracker.totalInRange() - shown;

        String header = Component.translatable("itemesp.hud.header", tracker.totalInRange(), tracker.effectiveRadius()).getString();
        String more = hidden > 0 ? Component.translatable("itemesp.hud.more", hidden).getString() : null;
        String[] rows = new String[shown];
        int width = font.width(header);
        for (int i = 0; i < shown; i++) {
            TrackedItem tracked = items.get(i);
            rows[i] = describe(tracked.stack(), tracked.distance()).getString();
            width = Math.max(width, SWATCH + 4 + font.width(rows[i]));
        }
        if (more != null) {
            width = Math.max(width, font.width(more));
        }

        int height = font.lineHeight + 2 + shown * ROW_HEIGHT + (more != null ? font.lineHeight + 2 : 0);
        int x = MARGIN + PADDING;
        int y = MARGIN + PADDING;
        graphics.fill(MARGIN, MARGIN, x + width + PADDING, y + height + PADDING, PANEL_COLOR);

        graphics.text(font, header, x, y, HEADER_COLOR);
        y += font.lineHeight + 2;
        for (int i = 0; i < shown; i++) {
            int color = EspColors.withAlpha(items.get(i).color(), 255);
            // A color swatch matching the item's box and tracer.
            graphics.fill(x, y + 1, x + SWATCH, y + 1 + SWATCH, color);
            graphics.text(font, rows[i], x + SWATCH + 4, y, color);
            y += ROW_HEIGHT;
        }
        if (more != null) {
            graphics.text(font, more, x, y, MUTED_COLOR);
        }
    }
}
