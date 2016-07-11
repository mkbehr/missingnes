#version 330

in vec2 pos;
in vec2 scroll;
//uniform vec2 map_size;

in vec3 v_tuv;
in float v_palette_n; // Why are these floats? I don't know, but it works.

out vec2 f_uv;
out vec4[4] f_palette;

uniform vec4[16] localPalettes;

void main()
{
  // TODO: y coord should wrap if we're rendering a bg tile,
  // but not if we're rendering a sprite

  // TODO: backgrounds scroll, but not sprites

  // Note: not actually using map_size right now
  gl_Position = vec4( ((pos.x - scroll.x) / (16.0*8.0)) - 1,
                      ((pos.y - scroll.y) / (15.0*8.0)) - 1,
                      0.0,
                      1.0);
  // gl_Position = vec4(((float(xy.x) + (x_high * 256)) / (16.0*8.0)) - 1,
  //                    (float(xy.y) / (15.0*8.0)) - 1, 0.0, 1.0);
  f_uv = vec2((float(v_tuv.y) / 256.0) + float(v_tuv.x) / 256.0, float(v_tuv.z));
  for (int i = 0; i < 4; i++) {
    f_palette[i] = localPalettes[i + int(v_palette_n)*4];
  }
}
