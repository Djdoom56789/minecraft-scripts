package com.djdoom.itemesp.tracker;

import com.djdoom.itemesp.ItemEspClient;
import com.djdoom.itemesp.config.ItemEspConfig;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Finds dropped items around the player once per client tick.
 *
 * <p>The scan area is a square of chunks centered on the player's chunk,
 * {@code 2 * radius + 1} chunks wide, the same shape the game uses for
 * render distance. Rendering reads the latest snapshot, so the per-frame
 * cost stays independent of how many entities the world has loaded.
 */
public final class ItemTracker {
    /** Vertical extent of the scan; covers every world height. */
    private static final double SCAN_HEIGHT = 4096;

    private List<TrackedItem> items = List.of();
    private int totalInRange;
    private int effectiveRadius;

    public void tick(Minecraft client, ItemEspConfig config) {
        ClientLevel level = client.level;
        LocalPlayer player = client.player;
        if (!config.enabled || level == null || player == null || !ItemEspClient.isAllowed(client)) {
            clear();
            return;
        }

        // The client only knows about entities in chunks it has loaded, so a
        // radius beyond the render distance would only promise items it can't see.
        effectiveRadius = Math.min(config.chunkRadius, client.options.renderDistance().get());
        int radius = effectiveRadius;
        int centerX = Mth.floor(player.getX()) >> 4;
        int centerZ = Mth.floor(player.getZ()) >> 4;
        AABB area = new AABB(
                (centerX - radius) << 4, -SCAN_HEIGHT, (centerZ - radius) << 4,
                (centerX + radius + 1) << 4, SCAN_HEIGHT, (centerZ + radius + 1) << 4);

        List<ItemEntity> found = level.getEntitiesOfClass(ItemEntity.class, area, entity -> {
            if (!entity.isAlive()) {
                return false;
            }
            int chunkX = Mth.floor(entity.getX()) >> 4;
            int chunkZ = Mth.floor(entity.getZ()) >> 4;
            if (Math.abs(chunkX - centerX) > radius || Math.abs(chunkZ - centerZ) > radius) {
                return false;
            }
            ItemStack stack = entity.getItem();
            return !stack.isEmpty() && stack.getCount() >= config.minCount && config.isTracked(stack.getItem());
        });

        double maxDistance = (radius + 1) * 16.0;
        List<TrackedItem> scanned = new ArrayList<>(found.size());
        for (ItemEntity entity : found) {
            ItemStack stack = entity.getItem();
            double distance = entity.distanceTo(player);
            scanned.add(new TrackedItem(entity, stack, distance, EspColors.colorFor(stack, distance, maxDistance, config)));
        }
        scanned.sort(Comparator.comparingDouble(TrackedItem::distance));

        totalInRange = scanned.size();
        items = scanned.size() > config.maxItems ? List.copyOf(scanned.subList(0, config.maxItems)) : List.copyOf(scanned);
    }

    public void clear() {
        items = List.of();
        totalInRange = 0;
    }

    /** Tracked items, nearest first, capped at the configured maximum. */
    public List<TrackedItem> items() {
        return items;
    }

    /** Items in range before the max-items cap was applied. */
    public int totalInRange() {
        return totalInRange;
    }

    /** Radius actually scanned, after clamping to the render distance. */
    public int effectiveRadius() {
        return effectiveRadius;
    }
}
