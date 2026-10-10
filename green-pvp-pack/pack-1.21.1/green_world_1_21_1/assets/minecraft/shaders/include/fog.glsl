#version 150

// Green World (Minecraft 1.21 / 1.21.1).
//
// Every world shader (blocks, entities, items, particles, armor, clouds,
// beacon beams, text) finishes by calling linear_fog, so grading the color
// here turns the whole game green from a plain resource pack: no OptiFine,
// Iris or mods needed.
//
// Hues are squeezed toward green instead of replaced, and lightness never
// changes, so things that looked different still look different: red turns
// yellow-green, blue turns teal, grays get a green tint, white stays white.
// linear_fog_fade and fog_distance are unchanged from vanilla.

const float GW_GREEN_HUE = 1.0 / 3.0;
const float GW_LEAN = 0.4;        // 0 = vanilla colors, 1 = every hue becomes green
const float GW_GRAY_CAST = 0.15;  // minimum saturation, tints grays green

vec3 gw_rgb_to_hsl(vec3 c) {
    float maxc = max(c.r, max(c.g, c.b));
    float minc = min(c.r, min(c.g, c.b));
    float l = (maxc + minc) * 0.5;
    float d = maxc - minc;
    if (d < 1e-5) {
        return vec3(GW_GREEN_HUE, 0.0, l);
    }
    float s = l < 0.5 ? d / (maxc + minc) : d / (2.0 - maxc - minc);
    float h;
    if (maxc == c.r) {
        h = (c.g - c.b) / d + (c.g < c.b ? 6.0 : 0.0);
    } else if (maxc == c.g) {
        h = (c.b - c.r) / d + 2.0;
    } else {
        h = (c.r - c.g) / d + 4.0;
    }
    return vec3(h / 6.0, s, l);
}

float gw_channel(float p, float q, float t) {
    t = fract(t);
    if (t < 1.0 / 6.0) return p + (q - p) * 6.0 * t;
    if (t < 0.5) return q;
    if (t < 2.0 / 3.0) return p + (q - p) * (2.0 / 3.0 - t) * 6.0;
    return p;
}

vec3 gw_hsl_to_rgb(vec3 hsl) {
    float q = hsl.z < 0.5 ? hsl.z * (1.0 + hsl.y) : hsl.z + hsl.y - hsl.z * hsl.y;
    float p = 2.0 * hsl.z - q;
    return vec3(gw_channel(p, q, hsl.x + 1.0 / 3.0), gw_channel(p, q, hsl.x), gw_channel(p, q, hsl.x - 1.0 / 3.0));
}

vec3 green_world(vec3 color) {
    vec3 hsl = gw_rgb_to_hsl(clamp(color, 0.0, 1.0));
    float offset = fract(hsl.x - GW_GREEN_HUE + 0.5) - 0.5;
    hsl.x = fract(GW_GREEN_HUE + offset * (1.0 - GW_LEAN));
    // Magenta sits opposite green, where the squeeze splits neighbouring
    // purples into orange and blue. Fade saturation at that seam so purple
    // textures turn soft gray-green instead of speckled.
    hsl.y *= mix(1.0, 0.25, smoothstep(0.40, 0.5, abs(offset)));
    hsl.y = max(hsl.y, GW_GRAY_CAST);
    return gw_hsl_to_rgb(hsl);
}

vec4 linear_fog(vec4 inColor, float vertexDistance, float fogStart, float fogEnd, vec4 fogColor) {
    if (vertexDistance <= fogStart) {
        return vec4(green_world(inColor.rgb), inColor.a);
    }

    float fogValue = vertexDistance < fogEnd ? smoothstep(fogStart, fogEnd, vertexDistance) : 1.0;
    return vec4(green_world(mix(inColor.rgb, fogColor.rgb, fogValue * fogColor.a)), inColor.a);
}

float linear_fog_fade(float vertexDistance, float fogStart, float fogEnd) {
    if (vertexDistance <= fogStart) {
        return 1.0;
    } else if (vertexDistance >= fogEnd) {
        return 0.0;
    }

    return smoothstep(fogEnd, fogStart, vertexDistance);
}

float fog_distance(vec3 pos, int shape) {
    if (shape == 0) {
        return length(pos);
    } else {
        float distXZ = length(pos.xz);
        float distY = abs(pos.y);
        return max(distXZ, distY);
    }
}
