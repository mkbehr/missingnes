#ifndef SCREEN_H
#define SCREEN_H

#include <vector>

#define GLFW_INCLUDE_GLCOREARB
// defining GLFW_INCLUDE_GLEXT may also be useful in the future
#include <GLFW/glfw3.h>

struct bgVertex {
  unsigned char x_low;
  unsigned char y;
  unsigned char x_high;
  unsigned char tile;
  unsigned char u;
  unsigned char v;
  unsigned char palette;
};
// this may not be necessary now that we can just define a struct
const int VERTEX_ELTS = sizeof(struct bgVertex);

const char *PROGRAM_NAME = "Missingnes";

// TODO add more constants from the top of screen.py here

const char *VERTEX_SHADER_FILE = "vertex.vert";
const char *FRAGMENT_SHADER_FILE = "fragment.frag";

// some of these came from ppu.py, so they're a bit duplicated
const int SCANLINES = 262;
const int VISIBLE_SCANLINES = 240;
const int CYCLES_PER_SCANLINE = 341;
const int VISIBLE_COLUMNS = 256;

const int TILE_ROWS = VISIBLE_SCANLINES/8;
const int TILE_COLUMNS = VISIBLE_COLUMNS/8;

const int SCREEN_WIDTH = VISIBLE_COLUMNS;
const int SCREEN_HEIGHT = VISIBLE_SCANLINES;

const int VERTICES_PER_TILE = 6;

const int N_BG_VERTICES = TILE_ROWS * TILE_COLUMNS * VERTICES_PER_TILE;

const int PATTERN_TABLE_TILES = 256;
const int PATTERN_TABLE_LENGTH = PATTERN_TABLE_TILES * 8 * 8;

const GLenum BG_PATTERN_TABLE_TEXTURE = GL_TEXTURE0;
const int BG_PATTERN_TABLE_TEXID = 0;
const GLenum SPRITE_PATTERN_TABLE_TEXTURE = GL_TEXTURE1;
const int SPRITE_PATTERN_TABLE_TEXID = 1;
// TODO other texture ids go here

const int DRAW_BG = 1;
const int DRAW_SPRITES = 0;

const int LOCAL_PALETTES_LENGTH = 16*4;

const float FPS_UPDATE_INTERVAL = 2.0; // in seconds
const int MAX_FPS = 60;
const float SECONDS_PER_FRAME = 1.0 / MAX_FPS;

// gain determining seconds per frame (as in a kalman filter)
const float SPF_GAIN = 0.2;

class Screen {
 public:
  Screen();

  void setUniversalBg(int);
  void setLocalPalettes(vector<float>);
  void setLocalPalettes(float*);
  void setBgPatternTable(vector<float>);
  void setBgPatternTable(float*);
  void setSpritePatternTable(vector<float>);
  void setSpritePatternTable(float*);
  void setTileIndices(vector<vector<unsigned char> >);
  void setTileIndices(unsigned char *);
  void setPaletteIndices(vector<vector<unsigned char> >);
  void setPaletteIndices(unsigned char *);

  void testRenderLoop();
  void drawToBuffer();
  int draw();

 private:
  GLFWwindow *window;
  GLuint shader;
  // shader attribute locations
  GLint xyAttrib;
  GLint xHighAttrib;
  GLint tuvAttrib;
  GLint paletteNAttrib;

  // buffers
  GLuint bgVbo;
  GLuint spriteVbo;
  // textures
  GLuint bgPtabName;
  GLuint spritePtabName;


  // PPU state trackers (unused here?)
  int lastBgPalette;
  int lastSpritePalette;

  // state
  vector<vector<unsigned char> > tileIndices;
  vector<vector<unsigned char> > paletteIndices;

  struct bgVertex bgVertices[N_BG_VERTICES];

  float localPalettes[LOCAL_PALETTES_LENGTH];

  int universalBg;

  // methods

  void initShaders();
  void initBgVertices();


};



int initWindow(GLFWwindow**);

void die();

#endif
