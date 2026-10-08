// Shared fragment stage for entities and the held item. Output 0 is the normal
// color; output 1 (colortex2) is a mask final.fsh uses to grade gear more
// gently, so iron, gold, diamond and netherite stay tellable apart.

uniform sampler2D gtexture;
uniform sampler2D lightmap;
uniform vec4 entityColor;  // red hurt flash / creeper white flash
uniform vec3 fogColor;
uniform float far;

varying vec2 texcoord;
varying vec2 lmcoord;
varying vec4 glcolor;
varying float viewDistance;

void main() {
    vec4 color = texture2D(gtexture, texcoord) * glcolor;
    if (color.a < 0.1) {
        discard;
    }
    color.rgb = mix(color.rgb, entityColor.rgb, entityColor.a);
    color *= texture2D(lightmap, lmcoord);

    float fog = clamp((viewDistance - far * 0.8) / (far * 0.2), 0.0, 1.0);
    color.rgb = mix(color.rgb, fogColor, fog);

/* DRAWBUFFERS:02 */
    gl_FragData[0] = color;
    gl_FragData[1] = vec4(1.0 - fog, 0.0, 0.0, 1.0);
}
