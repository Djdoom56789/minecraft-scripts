package com.djdoom.itemesp.render;

import com.djdoom.itemesp.config.ItemEspConfig;
import com.djdoom.itemesp.tracker.EspColors;
import com.djdoom.itemesp.tracker.ItemTracker;
import com.djdoom.itemesp.tracker.TrackedItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.fabricmc.fabric.api.client.rendering.v1.level.LevelRenderContext;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.rendertype.RenderTypes;
import net.minecraft.client.renderer.state.level.CameraRenderState;
import net.minecraft.network.chat.Component;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.List;
import java.util.function.Supplier;

/**
 * Draws boxes, tracers and floating labels for tracked items.
 *
 * <p>Lines are thin ribbons (quads) turned to face the camera, submitted
 * through the same debug box render type Fabric's own render tests use.
 * Geometry is built in world space with the pose stack shifted by the
 * camera position, as the Fabric example does.
 */
public final class EspRenderer {
    /** Labels past this count are skipped; text is far costlier than lines. */
    private static final int MAX_LABELS = 64;
    private static final int LINE_ALPHA = 220;
    private static final int SCAN_AREA_COLOR = 0x55FFFF;
    /** Ribbon half-width in blocks per point of the "Line Width" setting. */
    private static final double WIDTH_PER_POINT = 0.008;
    private static final int FULL_BRIGHT = 0xF000F0;

    private final Supplier<ItemEspConfig> config;
    private final ItemTracker tracker;

    public EspRenderer(Supplier<ItemEspConfig> config, ItemTracker tracker) {
        this.config = config;
        this.tracker = tracker;
    }

    public void render(LevelRenderContext context) {
        ItemEspConfig cfg = config.get();
        Minecraft client = Minecraft.getInstance();
        List<TrackedItem> items = tracker.items();
        if (!cfg.enabled || client.player == null || (items.isEmpty() && !cfg.showScanArea)) {
            return;
        }

        CameraRenderState camera = context.levelState().cameraRenderState;
        Vec3 cameraPos = camera.pos;
        double halfWidth = cfg.lineWidth * WIDTH_PER_POINT;
        // Tracers start a little in front of the eye, toward the crosshair.
        Vec3 tracerStart = cameraPos.add(client.player.getLookAngle().scale(0.6));

        PoseStack poseStack = context.poseStack();
        boolean anyLines = !items.isEmpty() && (cfg.boxes || cfg.tracers);
        if (anyLines || cfg.showScanArea) {
            poseStack.pushPose();
            poseStack.translate(-cameraPos.x, -cameraPos.y, -cameraPos.z);
            context.submitNodeCollector().submitCustomGeometry(poseStack, RenderTypes.debugFilledBox(), (pose, buffer) -> {
                for (TrackedItem tracked : items) {
                    int argb = EspColors.withAlpha(tracked.color(), LINE_ALPHA);
                    AABB box = tracked.entity().getBoundingBox();
                    if (cfg.boxes) {
                        box(buffer, pose, box, cameraPos, halfWidth, argb);
                    }
                    if (cfg.tracers) {
                        ribbon(buffer, pose, tracerStart, box.getCenter(), cameraPos, halfWidth, argb);
                    }
                }
                if (cfg.showScanArea) {
                    scanArea(buffer, pose, client, cameraPos, halfWidth);
                }
            });
            poseStack.popPose();
        }

        if (cfg.labels) {
            int count = Math.min(items.size(), MAX_LABELS);
            for (int i = 0; i < count; i++) {
                TrackedItem tracked = items.get(i);
                ItemEntity entity = tracked.entity();
                Vec3 pos = entity.position();
                poseStack.pushPose();
                poseStack.translate(pos.x - cameraPos.x, pos.y - cameraPos.y, pos.z - cameraPos.z);
                Component label = HudOverlay.describe(tracked.stack(), tracked.distance())
                        .withColor(tracked.color());
                context.submitNodeCollector().order(0).submitNameTag(poseStack,
                        new Vec3(0, entity.getBbHeight() + 0.3, 0), 0, label, cfg.throughWalls, FULL_BRIGHT, camera);
                poseStack.popPose();
            }
        }
    }

    /** Outlines the scanned chunk square at the player's feet. */
    private void scanArea(VertexConsumer buffer, PoseStack.Pose pose, Minecraft client, Vec3 cameraPos, double halfWidth) {
        int radius = tracker.effectiveRadius();
        int centerX = Mth.floor(client.player.getX()) >> 4;
        int centerZ = Mth.floor(client.player.getZ()) >> 4;
        double y = client.player.getY() + 0.05;
        double minX = (centerX - radius) << 4;
        double minZ = (centerZ - radius) << 4;
        double maxX = (centerX + radius + 1) << 4;
        double maxZ = (centerZ + radius + 1) << 4;
        int argb = EspColors.withAlpha(SCAN_AREA_COLOR, 160);
        ribbon(buffer, pose, new Vec3(minX, y, minZ), new Vec3(maxX, y, minZ), cameraPos, halfWidth, argb);
        ribbon(buffer, pose, new Vec3(maxX, y, minZ), new Vec3(maxX, y, maxZ), cameraPos, halfWidth, argb);
        ribbon(buffer, pose, new Vec3(maxX, y, maxZ), new Vec3(minX, y, maxZ), cameraPos, halfWidth, argb);
        ribbon(buffer, pose, new Vec3(minX, y, maxZ), new Vec3(minX, y, minZ), cameraPos, halfWidth, argb);
    }

    private static void box(VertexConsumer buffer, PoseStack.Pose pose, AABB b, Vec3 cam, double w, int argb) {
        Vec3[] c = {
                new Vec3(b.minX, b.minY, b.minZ), new Vec3(b.maxX, b.minY, b.minZ),
                new Vec3(b.maxX, b.minY, b.maxZ), new Vec3(b.minX, b.minY, b.maxZ),
                new Vec3(b.minX, b.maxY, b.minZ), new Vec3(b.maxX, b.maxY, b.minZ),
                new Vec3(b.maxX, b.maxY, b.maxZ), new Vec3(b.minX, b.maxY, b.maxZ),
        };
        int[][] edges = {{0, 1}, {1, 2}, {2, 3}, {3, 0}, {4, 5}, {5, 6}, {6, 7}, {7, 4}, {0, 4}, {1, 5}, {2, 6}, {3, 7}};
        for (int[] e : edges) {
            ribbon(buffer, pose, c[e[0]], c[e[1]], cam, w, argb);
        }
    }

    /**
     * A flat strip from a to b, widened sideways relative to the camera so it
     * always faces the viewer. Both windings are emitted so it shows whether
     * or not the render type culls back faces.
     */
    private static void ribbon(VertexConsumer buffer, PoseStack.Pose pose, Vec3 a, Vec3 b, Vec3 cam, double w, int argb) {
        Vec3 along = b.subtract(a);
        Vec3 toCamera = cam.subtract(a.add(b).scale(0.5));
        Vec3 side = along.cross(toCamera);
        if (side.lengthSqr() < 1.0e-12) {
            return;
        }
        side = side.normalize().scale(w);
        Vec3 p1 = a.add(side);
        Vec3 p2 = b.add(side);
        Vec3 p3 = b.subtract(side);
        Vec3 p4 = a.subtract(side);
        quad(buffer, pose, p1, p2, p3, p4, argb);
        quad(buffer, pose, p4, p3, p2, p1, argb);
    }

    private static void quad(VertexConsumer buffer, PoseStack.Pose pose, Vec3 a, Vec3 b, Vec3 c, Vec3 d, int argb) {
        buffer.addVertex(pose, (float) a.x, (float) a.y, (float) a.z).setColor(argb);
        buffer.addVertex(pose, (float) b.x, (float) b.y, (float) b.z).setColor(argb);
        buffer.addVertex(pose, (float) c.x, (float) c.y, (float) c.z).setColor(argb);
        buffer.addVertex(pose, (float) d.x, (float) d.y, (float) d.z).setColor(argb);
    }
}
