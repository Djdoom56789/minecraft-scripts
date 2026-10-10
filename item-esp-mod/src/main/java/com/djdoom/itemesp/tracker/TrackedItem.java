package com.djdoom.itemesp.tracker;

import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.ItemStack;

/**
 * A dropped item picked up by the last scan.
 *
 * @param entity   the live item entity
 * @param stack    the item stack the entity carries
 * @param distance distance from the player in blocks at scan time
 * @param color    RGB color chosen by the active {@link com.djdoom.itemesp.config.ColorMode}
 */
public record TrackedItem(ItemEntity entity, ItemStack stack, double distance, int color) {
}
