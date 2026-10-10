package com.djdoom.itemesp.gui;

import com.djdoom.itemesp.config.ItemEspConfig;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import org.jspecify.annotations.Nullable;

import java.util.function.BooleanSupplier;
import java.util.function.Consumer;
import java.util.function.IntFunction;
import java.util.function.IntSupplier;
import java.util.function.IntUnaryOperator;

/**
 * Main settings menu, opened with the menu key (default U).
 *
 * <p>Built only from plain buttons: on/off settings show "Name: ON" and
 * toggle on click; number settings have - and + buttons around a label.
 */
public final class ItemEspScreen extends Screen {
    private static final int COLUMN_WIDTH = 150;
    private static final int BUTTON_HEIGHT = 20;
    private static final int GAP = 4;
    private static final int ROW = BUTTON_HEIGHT + 2;
    private static final int STEP_WIDTH = 20;
    private static final int TOP = 32;

    @Nullable
    private final Screen parent;
    private final ItemEspConfig config;

    public ItemEspScreen(@Nullable Screen parent, ItemEspConfig config) {
        super(Component.translatable("itemesp.title"));
        this.parent = parent;
        this.config = config;
    }

    @Override
    protected void init() {
        int left = this.width / 2 - COLUMN_WIDTH - GAP / 2;
        int right = this.width / 2 + GAP / 2;
        int y = TOP;

        toggle(left, y, "itemesp.option.enabled", () -> config.enabled, v -> config.enabled = v);
        toggle(right, y, "itemesp.option.through_walls", () -> config.throughWalls, v -> config.throughWalls = v);
        y += ROW;
        toggle(left, y, "itemesp.option.tracers", () -> config.tracers, v -> config.tracers = v);
        toggle(right, y, "itemesp.option.boxes", () -> config.boxes, v -> config.boxes = v);
        y += ROW;
        toggle(left, y, "itemesp.option.labels", () -> config.labels, v -> config.labels = v);
        toggle(right, y, "itemesp.option.hud", () -> config.hud, v -> config.hud = v);
        y += ROW;
        toggle(left, y, "itemesp.option.scan_area", () -> config.showScanArea, v -> config.showScanArea = v);
        this.addRenderableWidget(Button.builder(colorLabel(), button -> {
                    config.colorMode = config.colorMode.next();
                    button.setMessage(colorLabel());
                })
                .pos(right, y).size(COLUMN_WIDTH, BUTTON_HEIGHT).build());
        y += ROW;

        stepper(left, y, "itemesp.option.chunk_radius", () -> config.chunkRadius,
                v -> config.chunkRadius = clamp(v, ItemEspConfig.MIN_CHUNK_RADIUS, ItemEspConfig.MAX_CHUNK_RADIUS),
                d -> d, String::valueOf);
        stepper(right, y, "itemesp.option.max_items", () -> config.maxItems,
                v -> config.maxItems = clamp(v, ItemEspConfig.MIN_MAX_ITEMS, ItemEspConfig.MAX_MAX_ITEMS),
                d -> d * (config.maxItems < 128 || (d < 0 && config.maxItems == 128) ? 16 : 128), String::valueOf);
        y += ROW;
        stepper(left, y, "itemesp.option.line_width", () -> Math.round(config.lineWidth * 2),
                v -> config.lineWidth = clamp(v, 2, 10) / 2.0f, d -> d, v -> String.valueOf(v / 2.0));
        stepper(right, y, "itemesp.option.hue", () -> config.fixedHue,
                v -> config.fixedHue = Math.floorMod(v, 360), d -> d * 15, String::valueOf);
        y += ROW;
        stepper(left, y, "itemesp.option.min_count", () -> config.minCount,
                v -> config.minCount = clamp(v, 1, ItemEspConfig.MAX_MIN_COUNT), d -> d, String::valueOf);
        y += ROW + GAP;

        int totalItems = BuiltInRegistries.ITEM.size() - 1; // minus air
        int tracked = Math.max(0, totalItems - config.ignoredItems.size());
        this.addRenderableWidget(Button.builder(Component.translatable("itemesp.button.filter", tracked, totalItems),
                        button -> this.minecraft.gui.setScreen(new ItemFilterScreen(this, config)))
                .pos(left, y).size(COLUMN_WIDTH * 2 + GAP, BUTTON_HEIGHT).build());
        y += ROW;

        this.addRenderableWidget(Button.builder(Component.translatable("itemesp.button.reset"), button -> {
                    config.resetToDefaults();
                    this.minecraft.gui.setScreen(new ItemEspScreen(parent, config));
                })
                .pos(left, y).size(COLUMN_WIDTH, BUTTON_HEIGHT).build());
        this.addRenderableWidget(Button.builder(Component.translatable("gui.done"), button -> this.onClose())
                .pos(right, y).size(COLUMN_WIDTH, BUTTON_HEIGHT).build());
    }

    private Component colorLabel() {
        return Component.translatable("itemesp.option.color_mode").append(": ").append(config.colorMode.displayName());
    }

    private void toggle(int x, int y, String key, BooleanSupplier getter, Consumer<Boolean> setter) {
        this.addRenderableWidget(Button.builder(onOff(key, getter.getAsBoolean()), button -> {
                    boolean value = !getter.getAsBoolean();
                    setter.accept(value);
                    button.setMessage(onOff(key, value));
                })
                .pos(x, y).size(COLUMN_WIDTH, BUTTON_HEIGHT).build());
    }

    private static Component onOff(String key, boolean on) {
        MutableComponent state = Component.translatable(on ? "itemesp.on" : "itemesp.off")
                .withStyle(on ? ChatFormatting.GREEN : ChatFormatting.RED);
        return Component.translatable(key).append(": ").append(state);
    }

    /**
     * [-] label [+]. step maps a direction (-1 or +1) to the amount to add;
     * format turns the stored value into the number shown in the label.
     */
    private void stepper(int x, int y, String key, IntSupplier getter, Consumer<Integer> setter,
                         IntUnaryOperator step, IntFunction<String> format) {
        Button label = Button.builder(Component.translatable(key, format.apply(getter.getAsInt())), button -> { })
                .pos(x + STEP_WIDTH + 2, y).size(COLUMN_WIDTH - 2 * (STEP_WIDTH + 2), BUTTON_HEIGHT).build();
        label.active = false;
        Runnable refresh = () -> label.setMessage(Component.translatable(key, format.apply(getter.getAsInt())));
        this.addRenderableWidget(Button.builder(Component.literal("-"), button -> {
                    setter.accept(getter.getAsInt() + step.applyAsInt(-1));
                    refresh.run();
                })
                .pos(x, y).size(STEP_WIDTH, BUTTON_HEIGHT).build());
        this.addRenderableWidget(label);
        this.addRenderableWidget(Button.builder(Component.literal("+"), button -> {
                    setter.accept(getter.getAsInt() + step.applyAsInt(1));
                    refresh.run();
                })
                .pos(x + COLUMN_WIDTH - STEP_WIDTH, y).size(STEP_WIDTH, BUTTON_HEIGHT).build());
    }

    private static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }

    @Override
    public void extractRenderState(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float delta) {
        this.extractBackground(graphics, mouseX, mouseY, delta);
        super.extractRenderState(graphics, mouseX, mouseY, delta);
        graphics.centeredText(this.font, this.title.getString(), this.width / 2, 10, 0xFFFFFFFF);

        int viewDistance = this.minecraft.options.renderDistance().get();
        if (config.chunkRadius > viewDistance) {
            graphics.centeredText(this.font, Component.translatable("itemesp.radius_limited", viewDistance).getString(),
                    this.width / 2, 21, 0xFFFFAA00);
        }
    }

    @Override
    public void onClose() {
        config.save();
        this.minecraft.gui.setScreen(parent);
    }
}
