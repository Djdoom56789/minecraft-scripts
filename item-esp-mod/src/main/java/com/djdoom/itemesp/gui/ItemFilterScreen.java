package com.djdoom.itemesp.gui;

import com.djdoom.itemesp.config.ItemEspConfig;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.Element;
import net.minecraft.client.gui.Selectable;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.client.gui.widget.ElementListWidget;
import net.minecraft.client.gui.widget.TextFieldWidget;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.item.Items;
import net.minecraft.registry.Registries;
import net.minecraft.screen.ScreenTexts;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;

import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/**
 * Lists every registered item (vanilla and modded) with a per-item toggle and
 * a search box. "Track All" / "Track None" apply to the items currently shown,
 * so searching "ore" then pressing Track None ignores just the ores.
 */
final class ItemFilterScreen extends Screen {
    private static final int LIST_TOP = 44;
    private static final int FOOTER_HEIGHT = 32;
    private static final int ROW_HEIGHT = 22;
    private static final int BUTTON_WIDTH = 100;

    private final Screen parent;
    private final ItemEspConfig config;
    private final List<ItemRow> allRows;
    private TextFieldWidget search;
    private ItemList list;

    ItemFilterScreen(Screen parent, ItemEspConfig config) {
        super(Text.translatable("itemesp.filter.title"));
        this.parent = parent;
        this.config = config;
        this.allRows = Registries.ITEM.stream()
                .filter(item -> item != Items.AIR)
                .map(ItemRow::new)
                .sorted(Comparator.comparing(row -> row.searchName))
                .toList();
    }

    @Override
    protected void init() {
        String previousQuery = search != null ? search.getText() : "";
        search = new TextFieldWidget(textRenderer, width / 2 - 150, 22, 300, 18, Text.translatable("itemesp.filter.search"));
        search.setPlaceholder(Text.translatable("itemesp.filter.search").formatted(Formatting.DARK_GRAY));
        search.setText(previousQuery);
        search.setChangedListener(query -> refreshList());
        addDrawableChild(search);

        list = new ItemList(client, width, height - LIST_TOP - FOOTER_HEIGHT, LIST_TOP);
        addDrawableChild(list);
        refreshList();

        int y = height - FOOTER_HEIGHT + 6;
        int x = width / 2 - (BUTTON_WIDTH * 3 + 8) / 2;
        addDrawableChild(ButtonWidget.builder(Text.translatable("itemesp.button.enable_all"), b -> setAllShown(true))
                .dimensions(x, y, BUTTON_WIDTH, 20).build());
        addDrawableChild(ButtonWidget.builder(Text.translatable("itemesp.button.disable_all"), b -> setAllShown(false))
                .dimensions(x + BUTTON_WIDTH + 4, y, BUTTON_WIDTH, 20).build());
        addDrawableChild(ButtonWidget.builder(ScreenTexts.DONE, b -> close())
                .dimensions(x + (BUTTON_WIDTH + 4) * 2, y, BUTTON_WIDTH, 20).build());

        setInitialFocus(search);
    }

    private void refreshList() {
        String query = search.getText().trim().toLowerCase(Locale.ROOT);
        List<Entry> shown = allRows.stream()
                .filter(row -> query.isEmpty() || row.searchName.contains(query) || row.id.contains(query))
                .map(Entry::new)
                .toList();
        list.setEntries(shown);
    }

    private void setAllShown(boolean tracked) {
        for (Entry entry : list.children()) {
            config.setTracked(entry.row.item, tracked);
            entry.updateLabel();
        }
    }

    @Override
    public void render(DrawContext context, int mouseX, int mouseY, float delta) {
        super.render(context, mouseX, mouseY, delta);
        context.drawCenteredTextWithShadow(textRenderer, title, width / 2, 8, 0xFFFFFF);
    }

    @Override
    public void close() {
        config.save();
        client.setScreen(parent);
    }

    /** Immutable per-item data, built once per screen. */
    private static final class ItemRow {
        final Item item;
        final ItemStack stack;
        final Text name;
        final String id;
        final String searchName;

        ItemRow(Item item) {
            this.item = item;
            this.stack = new ItemStack(item);
            this.name = item.getName();
            this.id = Registries.ITEM.getId(item).toString();
            this.searchName = name.getString().toLowerCase(Locale.ROOT);
        }
    }

    private final class ItemList extends ElementListWidget<Entry> {
        ItemList(MinecraftClient client, int width, int height, int y) {
            super(client, width, height, y, ROW_HEIGHT);
        }

        void setEntries(List<Entry> entries) {
            replaceEntries(entries);
            setScrollAmount(0);
        }

        @Override
        public int getRowWidth() {
            return 320;
        }
    }

    private final class Entry extends ElementListWidget.Entry<Entry> {
        private final ItemRow row;
        private final ButtonWidget toggle;

        Entry(ItemRow row) {
            this.row = row;
            this.toggle = ButtonWidget.builder(Text.empty(), button -> {
                config.setTracked(row.item, !config.isTracked(row.item));
                updateLabel();
            }).dimensions(0, 0, 70, 20).build();
            updateLabel();
        }

        void updateLabel() {
            boolean tracked = config.isTracked(row.item);
            toggle.setMessage(tracked
                    ? Text.translatable("itemesp.filter.on").formatted(Formatting.GREEN)
                    : Text.translatable("itemesp.filter.off").formatted(Formatting.RED));
        }

        @Override
        public void render(DrawContext context, int index, int y, int x, int entryWidth, int entryHeight,
                           int mouseX, int mouseY, boolean hovered, float tickDelta) {
            context.drawItem(row.stack, x + 2, y + 2);
            context.drawTextWithShadow(textRenderer, row.name, x + 24, y + 2, 0xFFFFFF);
            context.drawTextWithShadow(textRenderer, Text.literal(row.id), x + 24, y + 11, 0x808080);
            toggle.setX(x + entryWidth - toggle.getWidth() - 2);
            toggle.setY(y);
            toggle.render(context, mouseX, mouseY, tickDelta);
        }

        @Override
        public List<? extends Element> children() {
            return List.of(toggle);
        }

        @Override
        public List<? extends Selectable> selectableChildren() {
            return List.of(toggle);
        }
    }
}
