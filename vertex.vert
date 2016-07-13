#version 330

in vec2 pos;
in float priority;
in float tile;
in vec3 v_uv;
in float v_palette_n;

out vec2 f_uv;
out vec4[4] f_palette;

uniform vec4[16] localPalettes;

void main()
{
  // This converts from pixel-space coordinates to GL coordinates.
  // In GL coordinates, the y axis goes down-to-up.
  gl_Position = vec4( (pos.x / (16.0*8.0)) - 1,
                      1 - (pos.y / (15.0*8.0)),
                      priority,
                      1.0);
  f_uv = vec2((tile + v_uv.x)/256.0, v_uv.y);
  //f_uv = vec2((float(v_uv.x) / 256.0) + float(tile) / 256.0, float(v_uv.y));
  for (int i = 0; i < 4; i++) {
    f_palette[i] = localPalettes[i + int(v_palette_n)*4];
  }
}
