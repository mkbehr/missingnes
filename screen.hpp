#ifndef SCREEN_H
#define SCREEN_H

#include <vector>

#define GLFW_INCLUDE_GLCOREARB
// defining GLFW_INCLUDE_GLEXT may also be useful in the future
#include <GLFW/glfw3.h>

struct glVertex {
  unsigned char x_low;
  unsigned char y;
  unsigned char x_high;
  unsigned char tile;
  unsigned char u;
  unsigned char v;
  unsigned char palette;
};
// this may not be necessary now that we can just define a struct
const int VERTEX_ELTS = sizeof(struct glVertex);
static_assert(sizeof(struct glVertex) == 7, "glVertex struct has wrong size");

struct oamEntry {
  unsigned char y_minus_one;
  unsigned char tile;
  unsigned char attributes;
  unsigned char x;
};

static_assert(sizeof(struct oamEntry) == 4, "oamEntry struct has wrong size");

// Bitmasks for the attribute byte. I'd love to use a bitfield here
// instead, but bitfield ordering is implementation-specific and I
// don't want to tempt fate.
const unsigned char OAM_PALETTE = 0x3;
// bits 2-4 are unused
const unsigned char OAM_PRIORITY = 0x20;
const unsigned char OAM_FLIP_HORIZONTAL = 0x40;
const unsigned char OAM_FLIP_VERTICAL = 0x80;

const int OAM_ENTRIES = 64;
const int OAM_SIZE = 256;
static_assert(OAM_SIZE == OAM_ENTRIES * sizeof(struct oamEntry), "OAM size is wrong");

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
const int DRAW_SPRITES = 1;

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
  void setBgPalettes(vector<float>);
  void setBgPalettes(float*);
  void setBgPatternTable(vector<float>);
  void setBgPatternTable(float*);
  void setSpritePalettes(vector<float>);
  void setSpritePalettes(float*);
  void setSpritePatternTable(vector<float>);
  void setSpritePatternTable(float*);
  void setTileIndices(vector<vector<unsigned char> >);
  void setTileIndices(unsigned char *);
  void setPaletteIndices(vector<vector<unsigned char> >);
  void setPaletteIndices(unsigned char *);
  void setOam(unsigned char *);

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

  struct glVertex bgVertices[N_BG_VERTICES];

  float bgPalettes[LOCAL_PALETTES_LENGTH];

  int universalBg;

  struct oamEntry oam[OAM_ENTRIES];

  vector<struct glVertex> spriteVertices;

  float spritePalettes[LOCAL_PALETTES_LENGTH];

  // methods

  void initShaders();
  void initBgVertices();


};



int initWindow(GLFWwindow**);

void die();

#endif
