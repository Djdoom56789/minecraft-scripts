// Shared vertex stage for entities and the held item. Draws them the same way
// vanilla does; the fragment stage additionally marks them in colortex2.

varying vec2 texcoord;
varying vec2 lmcoord;
varying vec4 glcolor;
varying float viewDistance;

void main() {
    gl_Position = ftransform();
    texcoord = (gl_TextureMatrix[0] * gl_MultiTexCoord0).xy;
    lmcoord = (gl_TextureMatrix[1] * gl_MultiTexCoord1).xy;
    glcolor = gl_Color;
    viewDistance = length((gl_ModelViewMatrix * gl_Vertex).xyz);
}
