package com.djdoom.itemesp.tracker;

import net.minecraft.entity.ItemEntity;
import net.minecraft.item.ItemStack;

/**
 * A dropped item picked up by the last scan.
 *
 * @param entity   the live item entity (used for smooth interpolated rendering)
 * @param stack    the item stack the entity carries
 * @param distance distance from the player in blocks at scan time
 * @param color    RGB color chosen by the active {@link com.djdoom.itemesp.config.ColorMode}
 */
public record TrackedItem(ItemEntity entity, ItemStack stack, double distance, int color) {
}
