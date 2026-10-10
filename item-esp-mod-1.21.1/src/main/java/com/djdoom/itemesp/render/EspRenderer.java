package com.djdoom.itemesp.render;

import com.djdoom.itemesp.config.ItemEspConfig;
import com.djdoom.itemesp.tracker.EspColors;
import com.djdoom.itemesp.tracker.ItemTracker;
import com.djdoom.itemesp.tracker.TrackedItem;
import com.mojang.blaze3d.systems.RenderSystem;
import net.fabricmc.fabric.api.client.rendering.v1.WorldRenderContext;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.font.TextRenderer;
import net.minecraft.client.render.BufferBuilder;
import net.minecraft.client.render.BufferRenderer;
import net.minecraft.client.render.BuiltBuffer;
import net.minecraft.client.render.Camera;
import net.minecraft.client.render.GameRenderer;
import net.minecraft.client.render.LightmapTextureManager;
import net.minecraft.client.render.Tessellator;
import net.minecraft.client.render.VertexConsumerProvider;
import net.minecraft.client.render.VertexFormat;
import net.minecraft.client.render.VertexFormats;
import net.minecraft.client.util.math.MatrixStack;
import net.minecraft.entity.ItemEntity;
import net.minecraft.text.Text;
import net.minecraft.util.math.Box;
import net.minecraft.util.math.ChunkPos;
import net.minecraft.util.math.Vec3d;
import org.joml.Matrix4f;
import org.joml.Matrix4fStack;

import java.util.List;
import java.util.function.Supplier;

/**
 * Draws boxes, tracers and floating labels for tracked items after the world
 * has rendered. All geometry is expressed relative to the camera to avoid
 * float precision loss far from the world origin.
 */
public final class EspRenderer {
    /** Labels past this count are skipped; text is far costlier than lines. */
    private static final int MAX_LABELS = 64;
    private static final int LINE_ALPHA = 220;
    private static final int SCAN_AREA_COLOR = 0x55FFFF;
    private static final float LABEL_SCALE = 0.025f;
    private static final double LABEL_SCALE_START = 8.0;

    private final Supplier<ItemEspConfig> config;
    private final ItemTracker tracker;

    public EspRenderer(Supplier<ItemEspConfig> config, ItemTracker tracker) {
        this.config = config;
        this.tracker = tracker;
    }

    public void render(WorldRenderContext context) {
        ItemEspConfig cfg = config.get();
        MinecraftClient client = MinecraftClient.getInstance();
        List<TrackedItem> items = tracker.items();
        if (!cfg.enabled || client.player == null || (items.isEmpty() && !cfg.showScanArea)) {
            return;
        }

        Camera camera = context.camera();
        Vec3d cameraPos = camera.getPos();
        float tickDelta = context.tickCounter().getTickDelta(true);
        Matrix4f view = new Matrix4f(context.positionMatrix());

        // Vertices below already include the view transform, so make sure the
        // model-view matrix doesn't apply it a second time.
        Matrix4fStack modelView = RenderSystem.getModelViewStack();
        modelView.pushMatrix();
        modelView.identity();
        RenderSystem.applyModelViewMatrix();
        try {
            drawLines(cfg, client, items, camera, cameraPos, tickDelta, view);
            if (cfg.labels && !items.isEmpty()) {
                drawLabels(cfg, client, items, camera, cameraPos, tickDelta, view);
            }
        } finally {
            modelView.popMatrix();
            RenderSystem.applyModelViewMatrix();
        }
    }

    private void drawLines(ItemEspConfig cfg, MinecraftClient client, List<TrackedItem> items, Camera camera,
                           Vec3d cameraPos, float tickDelta, Matrix4f view) {
        boolean anyItemLines = !items.isEmpty() && (cfg.boxes || cfg.tracers);
        if (!anyItemLines && !cfg.showScanArea) {
            return;
        }

        RenderSystem.setShader(GameRenderer::getPositionColorProgram);
        RenderSystem.enableBlend();
        RenderSystem.defaultBlendFunc();
        RenderSystem.disableCull();
        RenderSystem.depthMask(false);
        if (cfg.throughWalls) {
            RenderSystem.disableDepthTest();
        } else {
            RenderSystem.enableDepthTest();
        }
        RenderSystem.lineWidth(cfg.lineWidth);

        BufferBuilder buffer = Tessellator.getInstance()
                .begin(VertexFormat.DrawMode.DEBUG_LINES, VertexFormats.POSITION_COLOR);

        // Tracers start just in front of the eye along the view direction so
        // they converge on the crosshair instead of collapsing to a point.
        Vec3d tracerStart = Vec3d.fromPolar(camera.getPitch(), camera.getYaw()).multiply(0.5);

        for (TrackedItem tracked : items) {
            ItemEntity entity = tracked.entity();
            Box box = interpolatedBox(entity, tickDelta).offset(cameraPos.negate());
            int argb = EspColors.withAlpha(tracked.color(), LINE_ALPHA);
            if (cfg.boxes) {
                box(buffer, view, box, argb);
            }
            if (cfg.tracers) {
                Vec3d center = box.getCenter();
                line(buffer, view, tracerStart.x, tracerStart.y, tracerStart.z, center.x, center.y, center.z, argb);
            }
        }

        if (cfg.showScanArea) {
            scanArea(buffer, view, client, cameraPos, tickDelta);
        }

        BuiltBuffer built = buffer.endNullable();
        if (built != null) {
            BufferRenderer.drawWithGlobalProgram(built);
        }

        RenderSystem.lineWidth(1.0f);
        RenderSystem.enableDepthTest();
        RenderSystem.depthMask(true);
        RenderSystem.enableCull();
        RenderSystem.disableBlend();
    }

    private void drawLabels(ItemEspConfig cfg, MinecraftClient client, List<TrackedItem> items, Camera camera,
                            Vec3d cameraPos, float tickDelta, Matrix4f view) {
        TextRenderer textRenderer = client.textRenderer;
        VertexConsumerProvider.Immediate consumers = client.getBufferBuilders().getEntityVertexConsumers();
        TextRenderer.TextLayerType layer = cfg.throughWalls
                ? TextRenderer.TextLayerType.SEE_THROUGH
                : TextRenderer.TextLayerType.NORMAL;
        int background = (int) (client.options.getTextBackgroundOpacity(0.25f) * 255.0f) << 24;

        MatrixStack matrices = new MatrixStack();
        matrices.multiplyPositionMatrix(view);

        int count = Math.min(items.size(), MAX_LABELS);
        for (int i = 0; i < count; i++) {
            TrackedItem tracked = items.get(i);
            ItemEntity entity = tracked.entity();
            Vec3d pos = entity.getLerpedPos(tickDelta).subtract(cameraPos);
            double distance = pos.length();

            matrices.push();
            matrices.translate(pos.x, pos.y + entity.getHeight() + 0.4, pos.z);
            matrices.multiply(camera.getRotation());
            // Grow labels with distance so far-away items stay readable.
            float scale = LABEL_SCALE * (float) Math.max(1.0, distance / LABEL_SCALE_START);
            matrices.scale(scale, -scale, scale);

            Text label = HudOverlay.describe(tracked.stack(), distance);
            float x = -textRenderer.getWidth(label) / 2.0f;
            textRenderer.draw(label, x, 0, EspColors.withAlpha(tracked.color(), 255), false,
                    matrices.peek().getPositionMatrix(), consumers, layer, background,
                    LightmapTextureManager.MAX_LIGHT_COORDINATE);
            matrices.pop();
        }
        consumers.draw();
    }

    private static Box interpolatedBox(ItemEntity entity, float tickDelta) {
        Vec3d lerped = entity.getLerpedPos(tickDelta);
        return entity.getBoundingBox().offset(lerped.subtract(entity.getPos()));
    }

    /** Outlines the scanned chunk square at the player's feet. */
    private void scanArea(BufferBuilder buffer, Matrix4f view, MinecraftClient client, Vec3d cameraPos,
                          float tickDelta) {
        ChunkPos center = client.player.getChunkPos();
        int radius = tracker.effectiveRadius();
        double y = client.player.getLerpedPos(tickDelta).y - cameraPos.y + 0.05;
        double minX = ((center.x - radius) << 4) - cameraPos.x;
        double minZ = ((center.z - radius) << 4) - cameraPos.z;
        double maxX = ((center.x + radius + 1) << 4) - cameraPos.x;
        double maxZ = ((center.z + radius + 1) << 4) - cameraPos.z;
        int argb = EspColors.withAlpha(SCAN_AREA_COLOR, 160);
        line(buffer, view, minX, y, minZ, maxX, y, minZ, argb);
        line(buffer, view, maxX, y, minZ, maxX, y, maxZ, argb);
        line(buffer, view, maxX, y, maxZ, minX, y, maxZ, argb);
        line(buffer, view, minX, y, maxZ, minX, y, minZ, argb);
    }

    private static void box(BufferBuilder buffer, Matrix4f view, Box b, int argb) {
        // Bottom face
        line(buffer, view, b.minX, b.minY, b.minZ, b.maxX, b.minY, b.minZ, argb);
        line(buffer, view, b.maxX, b.minY, b.minZ, b.maxX, b.minY, b.maxZ, argb);
        line(buffer, view, b.maxX, b.minY, b.maxZ, b.minX, b.minY, b.maxZ, argb);
        line(buffer, view, b.minX, b.minY, b.maxZ, b.minX, b.minY, b.minZ, argb);
        // Top face
        line(buffer, view, b.minX, b.maxY, b.minZ, b.maxX, b.maxY, b.minZ, argb);
        line(buffer, view, b.maxX, b.maxY, b.minZ, b.maxX, b.maxY, b.maxZ, argb);
        line(buffer, view, b.maxX, b.maxY, b.maxZ, b.minX, b.maxY, b.maxZ, argb);
        line(buffer, view, b.minX, b.maxY, b.maxZ, b.minX, b.maxY, b.minZ, argb);
        // Vertical edges
        line(buffer, view, b.minX, b.minY, b.minZ, b.minX, b.maxY, b.minZ, argb);
        line(buffer, view, b.maxX, b.minY, b.minZ, b.maxX, b.maxY, b.minZ, argb);
        line(buffer, view, b.maxX, b.minY, b.maxZ, b.maxX, b.maxY, b.maxZ, argb);
        line(buffer, view, b.minX, b.minY, b.maxZ, b.minX, b.maxY, b.maxZ, argb);
    }

    private static void line(BufferBuilder buffer, Matrix4f view, double x1, double y1, double z1,
                             double x2, double y2, double z2, int argb) {
        buffer.vertex(view, (float) x1, (float) y1, (float) z1).color(argb);
        buffer.vertex(view, (float) x2, (float) y2, (float) z2).color(argb);
    }
}
