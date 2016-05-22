#version 330

in vec2 f_uv;
in vec4[4] f_palette;

out vec4 outColor;

uniform sampler2D patternTable;

uniform float[16] localPalettes;

void main()
{
  float localPaletteIndex;
  localPaletteIndex = texture(patternTable, f_uv).r;
  // for now, assume localPaletteIndex will always be valid
  outColor = f_palette[int(localPaletteIndex)];
}