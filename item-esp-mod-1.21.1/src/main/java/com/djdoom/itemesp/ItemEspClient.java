package com.djdoom.itemesp;

import com.djdoom.itemesp.config.ItemEspConfig;
import com.djdoom.itemesp.gui.ItemEspScreen;
import com.djdoom.itemesp.render.EspRenderer;
import com.djdoom.itemesp.render.HudOverlay;
import com.djdoom.itemesp.tracker.ItemTracker;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;
import net.fabricmc.fabric.api.client.rendering.v1.WorldRenderEvents;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.option.KeyBinding;
import net.minecraft.client.util.InputUtil;
import net.minecraft.text.Text;
import org.lwjgl.glfw.GLFW;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Client entrypoint: wires config, key bindings, the tracker and renderers together. */
public final class ItemEspClient implements ClientModInitializer {
    public static final String MOD_ID = "itemesp";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    private static final String KEY_CATEGORY = "category.itemesp";

    private static ItemEspConfig config;
    private final ItemTracker tracker = new ItemTracker();

    private KeyBinding toggleKey;
    private KeyBinding menuKey;
    private KeyBinding radiusUpKey;
    private KeyBinding radiusDownKey;

    /**
     * The ESP only runs in single-player worlds (not when opened to LAN), so it
     * never gives an advantage over other players on a server.
     */
    public static boolean isAllowed(MinecraftClient client) {
        return client.isInSingleplayer();
    }

    public static ItemEspConfig config() {
        return config;
    }

    @Override
    public void onInitializeClient() {
        config = ItemEspConfig.load();

        toggleKey = register("key.itemesp.toggle", GLFW.GLFW_KEY_Y);
        menuKey = register("key.itemesp.menu", GLFW.GLFW_KEY_U);
        radiusUpKey = register("key.itemesp.radius_up", GLFW.GLFW_KEY_RIGHT_BRACKET);
        radiusDownKey = register("key.itemesp.radius_down", GLFW.GLFW_KEY_LEFT_BRACKET);

        ClientTickEvents.END_CLIENT_TICK.register(this::onTick);
        WorldRenderEvents.LAST.register(new EspRenderer(ItemEspClient::config, tracker)::render);
        HudRenderCallback.EVENT.register(new HudOverlay(ItemEspClient::config, tracker)::render);

        LOGGER.info("Item ESP loaded");
    }

    private static KeyBinding register(String translationKey, int defaultKey) {
        return KeyBindingHelper.registerKeyBinding(
                new KeyBinding(translationKey, InputUtil.Type.KEYSYM, defaultKey, KEY_CATEGORY));
    }

    private void onTick(MinecraftClient client) {
        while (menuKey.wasPressed()) {
            client.setScreen(new ItemEspScreen(client.currentScreen, config));
        }
        while (toggleKey.wasPressed()) {
            if (!guardSingleplayer(client)) {
                continue;
            }
            config.enabled = !config.enabled;
            config.save();
            notify(client, Text.translatable(config.enabled ? "itemesp.msg.toggled_on" : "itemesp.msg.toggled_off"));
        }
        while (radiusUpKey.wasPressed()) {
            changeRadius(client, 1);
        }
        while (radiusDownKey.wasPressed()) {
            changeRadius(client, -1);
        }

        tracker.tick(client, config);
    }

    private void changeRadius(MinecraftClient client, int delta) {
        if (!guardSingleplayer(client)) {
            return;
        }
        int radius = Math.max(ItemEspConfig.MIN_CHUNK_RADIUS,
                Math.min(ItemEspConfig.MAX_CHUNK_RADIUS, config.chunkRadius + delta));
        if (radius != config.chunkRadius) {
            config.chunkRadius = radius;
            config.save();
        }
        notify(client, Text.translatable("itemesp.msg.radius", radius));
    }

    private static boolean guardSingleplayer(MinecraftClient client) {
        if (isAllowed(client)) {
            return true;
        }
        notify(client, Text.translatable("itemesp.msg.singleplayer_only"));
        return false;
    }

    private static void notify(MinecraftClient client, Text message) {
        if (client.player != null) {
            client.player.sendMessage(message, true);
        }
    }
}
