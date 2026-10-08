package com.djdoom.itemesp.tracker;

import com.djdoom.itemesp.ItemEspClient;
import com.djdoom.itemesp.config.ItemEspConfig;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.client.world.ClientWorld;
import net.minecraft.entity.ItemEntity;
import net.minecraft.item.ItemStack;
import net.minecraft.util.math.Box;
import net.minecraft.util.math.ChunkPos;

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
    private List<TrackedItem> items = List.of();
    private int totalInRange;
    private int effectiveRadius;

    public void tick(MinecraftClient client, ItemEspConfig config) {
        ClientWorld world = client.world;
        ClientPlayerEntity player = client.player;
        if (!config.enabled || world == null || player == null || !ItemEspClient.isAllowed(client)) {
            clear();
            return;
        }

        // The client only knows about entities in chunks it has loaded, so a
        // radius beyond the render distance would only promise items it can't see.
        effectiveRadius = Math.min(config.chunkRadius, client.options.getClampedViewDistance());
        int radius = effectiveRadius;
        ChunkPos center = player.getChunkPos();
        Box area = new Box(
                (center.x - radius) << 4, world.getBottomY(), (center.z - radius) << 4,
                (center.x + radius + 1) << 4, world.getTopY(), (center.z + radius + 1) << 4);

        List<ItemEntity> found = world.getEntitiesByClass(ItemEntity.class, area, entity -> {
            if (!entity.isAlive()) {
                return false;
            }
            ChunkPos chunk = entity.getChunkPos();
            if (Math.abs(chunk.x - center.x) > radius || Math.abs(chunk.z - center.z) > radius) {
                return false;
            }
            ItemStack stack = entity.getStack();
            return !stack.isEmpty() && stack.getCount() >= config.minCount && config.isTracked(stack.getItem());
        });

        double maxDistance = (radius + 1) * 16.0;
        List<TrackedItem> scanned = new ArrayList<>(found.size());
        for (ItemEntity entity : found) {
            ItemStack stack = entity.getStack();
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
