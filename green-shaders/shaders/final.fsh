#version 120

/*
 * Green Shaders - single full-screen pass that grades the vanilla image green.
 * Works on OptiFine and Iris; every option below appears in the in-game
 * shader options menu.
 */

// 0 = Emerald tint, 1 = Night vision (monochrome green), 2 = Terminal (phosphor green)
#define STYLE 0 // [0 1 2]
#define GREEN_STRENGTH 0.60 // [0.00 0.10 0.20 0.30 0.40 0.50 0.60 0.70 0.80 0.90 1.00]
#define SATURATION 1.10 // [0.00 0.25 0.50 0.75 0.90 1.00 1.10 1.25 1.50 1.75 2.00]
#define BRIGHTNESS 0.00 // [-0.20 -0.15 -0.10 -0.05 0.00 0.05 0.10 0.15 0.20]
#define CONTRAST 1.05 // [0.80 0.90 1.00 1.05 1.10 1.20 1.30 1.50]
#define GAMMA 1.00 // [0.70 0.80 0.90 1.00 1.10 1.20 1.30]

#define VIGNETTE
#define VIGNETTE_STRENGTH 0.45 // [0.10 0.20 0.30 0.45 0.60 0.75 0.90]
#define GLOW
#define GLOW_STRENGTH 0.35 // [0.10 0.20 0.35 0.50 0.75 1.00]
//#define SCANLINES
#define SCANLINE_STRENGTH 0.15 // [0.05 0.10 0.15 0.25 0.35 0.50]
//#define GRAIN
#define GRAIN_STRENGTH 0.04 // [0.02 0.04 0.06 0.08 0.12]

uniform sampler2D colortex0;
uniform float viewWidth;
uniform float viewHeight;
uniform float frameTimeCounter;

varying vec2 texcoord;

const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);

float luminance(vec3 color) {
    return dot(color, LUMA);
}

// Cheap 9-tap bright-pass blur: only pixels brighter than the threshold bleed
// into their neighbours, which makes lights and the sky glow softly.
vec3 glow(vec2 uv) {
    vec2 px = vec2(1.0 / viewWidth, 1.0 / viewHeight) * 3.0;
    vec3 sum = vec3(0.0);
    for (int x = -1; x <= 1; x++) {
        for (int y = -1; y <= 1; y++) {
            vec3 s = texture2D(colortex0, uv + vec2(x, y) * px).rgb;
            sum += s * smoothstep(0.65, 1.0, luminance(s));
        }
    }
    return sum / 9.0;
}

vec3 applyStyle(vec3 color) {
    float luma = luminance(color);
#if STYLE == 0
    // Emerald: push the image toward green while keeping some original hue.
    vec3 tinted = color * vec3(0.70, 1.15, 0.70);
    vec3 graded = mix(tinted, vec3(0.30, 1.00, 0.45) * luma * 1.35, 0.45);
#elif STYLE == 1
    // Night vision: monochrome, lifted shadows, bright green highlights.
    vec3 graded = vec3(0.10, 1.00, 0.25) * pow(luma, 0.8) * 1.3;
#else
    // Terminal: hard phosphor green with crushed blacks.
    vec3 graded = vec3(0.20, 1.00, 0.30) * smoothstep(0.05, 0.85, luma);
#endif
    return mix(color, graded, GREEN_STRENGTH);
}

vec3 adjust(vec3 color) {
    float luma = luminance(color);
    color = mix(vec3(luma), color, SATURATION);
    color = (color - 0.5) * CONTRAST + 0.5 + BRIGHTNESS;
    color = pow(max(color, 0.0), vec3(1.0 / GAMMA));
    return color;
}

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    vec3 color = texture2D(colortex0, texcoord).rgb;

#ifdef GLOW
    color += glow(texcoord) * GLOW_STRENGTH;
#endif

    color = applyStyle(color);
    color = adjust(color);

#ifdef SCANLINES
    color *= 1.0 - SCANLINE_STRENGTH * (0.5 + 0.5 * sin(texcoord.y * viewHeight * 3.14159));
#endif

#ifdef GRAIN
    color += (hash(texcoord * vec2(viewWidth, viewHeight) + fract(frameTimeCounter) * 100.0) - 0.5) * GRAIN_STRENGTH;
#endif

#ifdef VIGNETTE
    vec2 centered = texcoord - 0.5;
    color *= 1.0 - VIGNETTE_STRENGTH * smoothstep(0.25, 0.75, length(centered) * 1.2);
#endif

    gl_FragData[0] = vec4(clamp(color, 0.0, 1.0), 1.0);
}
