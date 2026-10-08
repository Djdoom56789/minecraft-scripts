package com.djdoom.itemesp.gui;

import com.djdoom.itemesp.config.ColorMode;
import com.djdoom.itemesp.config.ItemEspConfig;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.client.gui.widget.CyclingButtonWidget;
import net.minecraft.registry.Registries;
import net.minecraft.screen.ScreenTexts;
import net.minecraft.text.Text;
import org.jetbrains.annotations.Nullable;

import java.util.function.Consumer;

/** Main settings menu, opened with the menu key (default U). */
public final class ItemEspScreen extends Screen {
    private static final int BUTTON_WIDTH = 150;
    private static final int BUTTON_HEIGHT = 20;
    private static final int GAP = 4;
    private static final int ROW = BUTTON_HEIGHT + GAP;
    private static final int TOP = 36;

    @Nullable
    private final Screen parent;
    private final ItemEspConfig config;

    public ItemEspScreen(@Nullable Screen parent, ItemEspConfig config) {
        super(Text.translatable("itemesp.title"));
        this.parent = parent;
        this.config = config;
    }

    @Override
    protected void init() {
        int left = width / 2 - BUTTON_WIDTH - GAP / 2;
        int right = width / 2 + GAP / 2;
        int fullWidth = BUTTON_WIDTH * 2 + GAP;
        int y = TOP;

        toggle(left, y, "itemesp.option.enabled", config.enabled, v -> config.enabled = v);
        toggle(right, y, "itemesp.option.through_walls", config.throughWalls, v -> config.throughWalls = v);
        y += ROW;
        toggle(left, y, "itemesp.option.tracers", config.tracers, v -> config.tracers = v);
        toggle(right, y, "itemesp.option.boxes", config.boxes, v -> config.boxes = v);
        y += ROW;
        toggle(left, y, "itemesp.option.labels", config.labels, v -> config.labels = v);
        toggle(right, y, "itemesp.option.hud", config.hud, v -> config.hud = v);
        y += ROW;
        toggle(left, y, "itemesp.option.scan_area", config.showScanArea, v -> config.showScanArea = v);
        addDrawableChild(CyclingButtonWidget.<ColorMode>builder(ColorMode::displayName)
                .values(ColorMode.values())
                .initially(config.colorMode)
                .build(right, y, BUTTON_WIDTH, BUTTON_HEIGHT, Text.translatable("itemesp.option.color_mode"),
                        (button, value) -> config.colorMode = value));
        y += ROW;

        addDrawableChild(new IntSlider(left, y, BUTTON_WIDTH, BUTTON_HEIGHT, "itemesp.option.chunk_radius",
                ItemEspConfig.MIN_CHUNK_RADIUS, ItemEspConfig.MAX_CHUNK_RADIUS, config.chunkRadius,
                v -> config.chunkRadius = v));
        addDrawableChild(new IntSlider(right, y, BUTTON_WIDTH, BUTTON_HEIGHT, "itemesp.option.max_items",
                ItemEspConfig.MIN_MAX_ITEMS, ItemEspConfig.MAX_MAX_ITEMS, config.maxItems,
                v -> config.maxItems = v));
        y += ROW;
        addDrawableChild(new IntSlider(left, y, BUTTON_WIDTH, BUTTON_HEIGHT, "itemesp.option.line_width",
                10, 50, Math.round(config.lineWidth * 10), v -> String.format("%.1f", v / 10.0),
                v -> config.lineWidth = v / 10.0f));
        addDrawableChild(new IntSlider(right, y, BUTTON_WIDTH, BUTTON_HEIGHT, "itemesp.option.hue",
                0, 359, config.fixedHue, v -> config.fixedHue = v));
        y += ROW;
        addDrawableChild(new IntSlider(left, y, BUTTON_WIDTH, BUTTON_HEIGHT, "itemesp.option.min_count",
                1, ItemEspConfig.MAX_MIN_COUNT, config.minCount, v -> config.minCount = v));
        y += ROW + GAP;

        int totalItems = Registries.ITEM.size() - 1; // minus air
        int tracked = Math.max(0, totalItems - config.ignoredItems.size());
        addDrawableChild(ButtonWidget.builder(Text.translatable("itemesp.button.filter", tracked, totalItems),
                        button -> client.setScreen(new ItemFilterScreen(this, config)))
                .dimensions(left, y, fullWidth, BUTTON_HEIGHT)
                .build());
        y += ROW;

        addDrawableChild(ButtonWidget.builder(Text.translatable("itemesp.button.reset"), button -> {
                    config.resetToDefaults();
                    clearAndInit();
                })
                .dimensions(left, y, BUTTON_WIDTH, BUTTON_HEIGHT)
                .build());
        addDrawableChild(ButtonWidget.builder(ScreenTexts.DONE, button -> close())
                .dimensions(right, y, BUTTON_WIDTH, BUTTON_HEIGHT)
                .build());
    }

    private void toggle(int x, int y, String key, boolean initial, Consumer<Boolean> setter) {
        addDrawableChild(CyclingButtonWidget.onOffBuilder(initial)
                .build(x, y, BUTTON_WIDTH, BUTTON_HEIGHT, Text.translatable(key),
                        (button, value) -> setter.accept(value)));
    }

    @Override
    public void render(DrawContext context, int mouseX, int mouseY, float delta) {
        super.render(context, mouseX, mouseY, delta);
        context.drawCenteredTextWithShadow(textRenderer, title, width / 2, 14, 0xFFFFFF);

        int viewDistance = client.options.getClampedViewDistance();
        if (config.chunkRadius > viewDistance) {
            context.drawCenteredTextWithShadow(textRenderer,
                    Text.translatable("itemesp.radius_limited", viewDistance), width / 2, 24, 0xFFAA00);
        }
    }

    @Override
    public void close() {
        config.save();
        client.setScreen(parent);
    }
}
