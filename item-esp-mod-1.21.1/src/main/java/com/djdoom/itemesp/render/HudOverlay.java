package com.djdoom.itemesp.render;

import com.djdoom.itemesp.ItemEspClient;
import com.djdoom.itemesp.config.ItemEspConfig;
import com.djdoom.itemesp.tracker.EspColors;
import com.djdoom.itemesp.tracker.ItemTracker;
import com.djdoom.itemesp.tracker.TrackedItem;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.font.TextRenderer;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.render.RenderTickCounter;
import net.minecraft.item.ItemStack;
import net.minecraft.text.MutableText;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;

import java.util.List;
import java.util.function.Supplier;

/** Corner panel listing the nearest tracked items. */
public final class HudOverlay {
    private static final int MARGIN = 4;
    private static final int PADDING = 3;
    private static final int ROW_HEIGHT = 18;
    private static final int PANEL_COLOR = 0x90000000;
    private static final int HEADER_COLOR = 0x55FF55;
    private static final int MUTED_COLOR = 0xAAAAAA;

    private final Supplier<ItemEspConfig> config;
    private final ItemTracker tracker;

    public HudOverlay(Supplier<ItemEspConfig> config, ItemTracker tracker) {
        this.config = config;
        this.tracker = tracker;
    }

    /** "Diamond x5 · 12m" — shared by the HUD and the in-world labels. */
    public static Text describe(ItemStack stack, double distance) {
        MutableText text = stack.getName().copy();
        if (stack.getCount() > 1) {
            text.append(" x" + stack.getCount());
        }
        return text.append(Text.literal(" · " + Math.round(distance) + "m").formatted(Formatting.GRAY));
    }

    public void render(DrawContext context, RenderTickCounter tickCounter) {
        MinecraftClient client = MinecraftClient.getInstance();
        ItemEspConfig cfg = config.get();
        if (!cfg.enabled || !cfg.hud || client.player == null || client.options.hudHidden
                || client.getDebugHud().shouldShowDebugHud()) {
            return;
        }
        TextRenderer font = client.textRenderer;

        if (!ItemEspClient.isAllowed(client)) {
            Text warning = Text.translatable("itemesp.hud.singleplayer_only");
            context.fill(MARGIN, MARGIN, MARGIN + font.getWidth(warning) + PADDING * 2,
                    MARGIN + font.fontHeight + PADDING * 2, PANEL_COLOR);
            context.drawTextWithShadow(font, warning, MARGIN + PADDING, MARGIN + PADDING, MUTED_COLOR);
            return;
        }

        List<TrackedItem> items = tracker.items();
        int shown = Math.min(items.size(), cfg.hudLines);
        int hidden = tracker.totalInRange() - shown;

        Text header = Text.translatable("itemesp.hud.header", tracker.totalInRange(), tracker.effectiveRadius());
        Text more = hidden > 0 ? Text.translatable("itemesp.hud.more", hidden) : null;
        Text[] rows = new Text[shown];
        int width = font.getWidth(header);
        for (int i = 0; i < shown; i++) {
            TrackedItem tracked = items.get(i);
            rows[i] = describe(tracked.stack(), tracked.distance());
            width = Math.max(width, 18 + font.getWidth(rows[i]));
        }
        if (more != null) {
            width = Math.max(width, font.getWidth(more));
        }

        int height = font.fontHeight + 2 + shown * ROW_HEIGHT + (more != null ? font.fontHeight + 2 : 0);
        int x = MARGIN + PADDING;
        int y = MARGIN + PADDING;
        context.fill(MARGIN, MARGIN, x + width + PADDING, y + height + PADDING, PANEL_COLOR);

        context.drawTextWithShadow(font, header, x, y, HEADER_COLOR);
        y += font.fontHeight + 2;
        for (int i = 0; i < shown; i++) {
            TrackedItem tracked = items.get(i);
            context.drawItem(tracked.stack(), x, y);
            context.drawTextWithShadow(font, rows[i], x + 18, y + (16 - font.fontHeight) / 2 + 1,
                    EspColors.withAlpha(tracked.color(), 255));
            y += ROW_HEIGHT;
        }
        if (more != null) {
            context.drawTextWithShadow(font, more, x, y, MUTED_COLOR);
        }
    }
}
