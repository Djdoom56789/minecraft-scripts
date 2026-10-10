package com.djdoom.itemesp.gui;

import com.djdoom.itemesp.config.ItemEspConfig;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/**
 * Every registered item (vanilla and modded) as a page of on/off buttons,
 * with a search box. "Track Shown" / "Ignore Shown" apply to every item
 * matching the search, so searching "ore" then pressing Ignore Shown
 * ignores just the ores.
 */
final class ItemFilterScreen extends Screen {
    private static final int COLUMNS = 2;
    private static final int CELL_WIDTH = 160;
    private static final int BUTTON_HEIGHT = 20;
    private static final int ROW = BUTTON_HEIGHT + 2;
    private static final int GRID_TOP = 56;
    private static final int FOOTER = 52;

    private final Screen parent;
    private final ItemEspConfig config;
    private final List<Entry> allEntries;
    private final List<Button> cells = new ArrayList<>();
    private List<Entry> matches = List.of();
    private int page;
    private String query = "";

    ItemFilterScreen(Screen parent, ItemEspConfig config) {
        super(Component.translatable("itemesp.filter.title"));
        this.parent = parent;
        this.config = config;
        List<Entry> entries = new ArrayList<>();
        for (Item item : BuiltInRegistries.ITEM) {
            if (item != Items.AIR) {
                entries.add(new Entry(item));
            }
        }
        entries.sort(Comparator.comparing(entry -> entry.searchName));
        this.allEntries = List.copyOf(entries);
    }

    private record Entry(Item item, Component name, String id, String searchName) {
        Entry(Item item) {
            this(item, new ItemStack(item).getHoverName(), ItemEspConfig.itemId(item),
                    new ItemStack(item).getHoverName().getString().toLowerCase(Locale.ROOT));
        }
    }

    private int rowsPerPage() {
        return Math.max(1, (this.height - GRID_TOP - FOOTER) / ROW);
    }

    @Override
    protected void init() {
        cells.clear();
        int gridLeft = this.width / 2 - (COLUMNS * CELL_WIDTH + 4) / 2;

        EditBox search = new EditBox(this.font, this.width / 2 - 150, 22, 300, 18,
                Component.translatable("itemesp.filter.search"));
        search.setValue(query);
        search.setResponder(value -> {
            query = value.trim().toLowerCase(Locale.ROOT);
            page = 0;
            refresh();
        });
        this.addRenderableWidget(search);

        int rows = rowsPerPage();
        for (int i = 0; i < rows * COLUMNS; i++) {
            int index = i;
            int x = gridLeft + (i % COLUMNS) * (CELL_WIDTH + 4);
            int y = GRID_TOP + (i / COLUMNS) * ROW;
            Button cell = Button.builder(Component.empty(), button -> {
                        Entry entry = entryAt(index);
                        if (entry != null) {
                            config.setTracked(entry.item, !config.isTracked(entry.item));
                            refresh();
                        }
                    })
                    .pos(x, y).size(CELL_WIDTH, BUTTON_HEIGHT).build();
            cells.add(this.addRenderableWidget(cell));
        }

        int footerY = this.height - FOOTER + 6;
        int bottomY = footerY + ROW;
        this.addRenderableWidget(Button.builder(Component.translatable("itemesp.button.prev"), b -> turnPage(-1))
                .pos(gridLeft, footerY).size(80, BUTTON_HEIGHT).build());
        this.addRenderableWidget(Button.builder(Component.translatable("itemesp.button.next"), b -> turnPage(1))
                .pos(gridLeft + COLUMNS * CELL_WIDTH + 4 - 80, footerY).size(80, BUTTON_HEIGHT).build());
        int third = (COLUMNS * CELL_WIDTH + 4 - 8) / 3;
        this.addRenderableWidget(Button.builder(Component.translatable("itemesp.button.enable_all"), b -> setAllShown(true))
                .pos(gridLeft, bottomY).size(third, BUTTON_HEIGHT).build());
        this.addRenderableWidget(Button.builder(Component.translatable("itemesp.button.disable_all"), b -> setAllShown(false))
                .pos(gridLeft + third + 4, bottomY).size(third, BUTTON_HEIGHT).build());
        this.addRenderableWidget(Button.builder(Component.translatable("gui.done"), b -> this.onClose())
                .pos(gridLeft + 2 * (third + 4), bottomY).size(third, BUTTON_HEIGHT).build());

        refresh();
    }

    private Entry entryAt(int cell) {
        int index = page * cells.size() + cell;
        return index < matches.size() ? matches.get(index) : null;
    }

    private int pageCount() {
        return Math.max(1, (matches.size() + cells.size() - 1) / Math.max(1, cells.size()));
    }

    private void turnPage(int delta) {
        page = Math.floorMod(page + delta, pageCount());
        refresh();
    }

    private void refresh() {
        matches = allEntries.stream()
                .filter(e -> query.isEmpty() || e.searchName.contains(query) || e.id.contains(query))
                .toList();
        page = Math.min(page, pageCount() - 1);
        for (int i = 0; i < cells.size(); i++) {
            Entry entry = entryAt(i);
            Button cell = cells.get(i);
            cell.visible = entry != null;
            if (entry != null) {
                boolean on = config.isTracked(entry.item);
                cell.setMessage(entry.name.copy()
                        .append(": ")
                        .append(Component.translatable(on ? "itemesp.on" : "itemesp.off")
                                .withStyle(on ? ChatFormatting.GREEN : ChatFormatting.RED)));
            }
        }
    }

    private void setAllShown(boolean tracked) {
        for (Entry entry : matches) {
            config.setTracked(entry.item, tracked);
        }
        refresh();
    }

    @Override
    public void extractRenderState(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float delta) {
        this.extractBackground(graphics, mouseX, mouseY, delta);
        super.extractRenderState(graphics, mouseX, mouseY, delta);
        graphics.centeredText(this.font, this.title.getString(), this.width / 2, 8, 0xFFFFFFFF);
        graphics.centeredText(this.font,
                Component.translatable("itemesp.filter.page", page + 1, pageCount(), matches.size()).getString(),
                this.width / 2, GRID_TOP - 12, 0xFFAAAAAA);
    }

    @Override
    public void onClose() {
        config.save();
        this.minecraft.gui.setScreen(parent);
    }
}
