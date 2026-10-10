package com.djdoom.itemesp;

import com.djdoom.itemesp.config.ItemEspConfig;
import com.djdoom.itemesp.gui.ItemEspScreen;
import com.djdoom.itemesp.render.EspRenderer;
import com.djdoom.itemesp.render.HudOverlay;
import com.djdoom.itemesp.tracker.ItemTracker;
import com.mojang.blaze3d.platform.InputConstants;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keymapping.v1.KeyMappingHelper;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;
import net.fabricmc.fabric.api.client.rendering.v1.level.LevelRenderEvents;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.server.IntegratedServer;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import org.lwjgl.sdl.SDLScancode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Client entrypoint: wires config, key mappings, the tracker and renderers together. */
public final class ItemEspClient implements ClientModInitializer {
    public static final String MOD_ID = "itemesp";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    private static ItemEspConfig config;
    private final ItemTracker tracker = new ItemTracker();

    private KeyMapping toggleKey;
    private KeyMapping menuKey;
    private KeyMapping radiusUpKey;
    private KeyMapping radiusDownKey;

    /**
     * The ESP only runs in single-player worlds (not when opened to LAN), so it
     * never gives an advantage over other players.
     */
    public static boolean isAllowed(Minecraft client) {
        IntegratedServer server = client.getSingleplayerServer();
        return server != null && !server.isPublished();
    }

    public static ItemEspConfig config() {
        return config;
    }

    @Override
    public void onInitializeClient() {
        config = ItemEspConfig.load();

        KeyMapping.Category category = KeyMapping.Category.register(Identifier.fromNamespaceAndPath(MOD_ID, "main"));
        toggleKey = register("key.itemesp.toggle", SDLScancode.SDL_SCANCODE_Y, category);
        menuKey = register("key.itemesp.menu", SDLScancode.SDL_SCANCODE_U, category);
        radiusUpKey = register("key.itemesp.radius_up", SDLScancode.SDL_SCANCODE_RIGHTBRACKET, category);
        radiusDownKey = register("key.itemesp.radius_down", SDLScancode.SDL_SCANCODE_LEFTBRACKET, category);

        ClientTickEvents.END_CLIENT_TICK.register(this::onTick);
        LevelRenderEvents.BEFORE_TRANSLUCENT_TERRAIN.register(new EspRenderer(ItemEspClient::config, tracker)::render);
        HudElementRegistry.addLast(Identifier.fromNamespaceAndPath(MOD_ID, "item_list"),
                new HudOverlay(ItemEspClient::config, tracker)::extractRenderState);

        LOGGER.info("Item ESP loaded");
    }

    private static KeyMapping register(String translationKey, int scancode, KeyMapping.Category category) {
        return KeyMappingHelper.registerKeyMapping(
                new KeyMapping(translationKey, InputConstants.Type.KEYBOARD, scancode, category));
    }

    private void onTick(Minecraft client) {
        while (menuKey.consumeClick()) {
            client.gui.setScreen(new ItemEspScreen(null, config));
        }
        while (toggleKey.consumeClick()) {
            if (!guardSingleplayer(client)) {
                continue;
            }
            config.enabled = !config.enabled;
            config.save();
            notify(client, Component.translatable(config.enabled ? "itemesp.msg.toggled_on" : "itemesp.msg.toggled_off"));
        }
        while (radiusUpKey.consumeClick()) {
            changeRadius(client, 1);
        }
        while (radiusDownKey.consumeClick()) {
            changeRadius(client, -1);
        }

        tracker.tick(client, config);
    }

    private void changeRadius(Minecraft client, int delta) {
        if (!guardSingleplayer(client)) {
            return;
        }
        int radius = Math.max(ItemEspConfig.MIN_CHUNK_RADIUS,
                Math.min(ItemEspConfig.MAX_CHUNK_RADIUS, config.chunkRadius + delta));
        if (radius != config.chunkRadius) {
            config.chunkRadius = radius;
            config.save();
        }
        notify(client, Component.translatable("itemesp.msg.radius", radius));
    }

    private static boolean guardSingleplayer(Minecraft client) {
        if (isAllowed(client)) {
            return true;
        }
        notify(client, Component.translatable("itemesp.msg.singleplayer_only"));
        return false;
    }

    private static void notify(Minecraft client, Component message) {
        if (client.player != null) {
            client.gui.hud.setOverlayMessage(message, false);
        }
    }
}
