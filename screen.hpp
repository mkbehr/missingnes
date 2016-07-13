#ifndef SCREEN_H
#define SCREEN_H

#include <vector>

#define GLFW_INCLUDE_GLCOREARB
// defining GLFW_INCLUDE_GLEXT may also be useful in the future
#include <GLFW/glfw3.h>

// Coordinates in pattern table space.
typedef float ptab_uv_coord;
const GLenum GL_PTAB_UV_COORD = GL_FLOAT;
typedef int ptab_tile_coord;
const GLenum GL_PTAB_TILE_COORD = GL_INT;
// Coordinates in nametable space.
typedef int ntab_coord;
const GLenum GL_NTAB_COORD = GL_INT;
// Coordinates in scroll space.
typedef int scroll_coord;
const GLenum GL_SCROLL_COORD = GL_INT;
// Coordinates in pixel space.
typedef int pixel_coord;
const GLenum GL_PIXEL_COORD = GL_INT;

// Right now we feed the x and y positions to the shader and also
// their scroll positions. Is that reasonable? Should we instead be
// dealing with that in our main code?
typedef struct glVertex {
  pixel_coord x_pos;
  pixel_coord y_pos;
  float priority; // z coordinate as far as gl's concerned
  ptab_tile_coord tile;
  ptab_uv_coord u;
  ptab_uv_coord v;
  unsigned char palette;
} glVertex;

typedef struct oamEntry {
  unsigned char y_minus_one;
  unsigned char tile;
  unsigned char attributes;
  unsigned char x;
} oamEntry;

static_assert(sizeof(struct oamEntry) == 4, "oamEntry struct has wrong size");

typedef struct scrollChange {
  scroll_coord ss_x_offset;
  scroll_coord ss_y_offset;
  // Naming mismatch between start/end and top/bottom is intentional.
  // Y coordinates do denote the top and bottom of the region in pixel
  // spaces, but X coordinates aren't the left/right of the region,
  // only the start/end of the top/bottom line.
  pixel_coord ps_x_start;
  pixel_coord ps_y_top;
} scrollChange;

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
const pixel_coord SCANLINES = 262;
const pixel_coord VISIBLE_SCANLINES = 240;
const pixel_coord CYCLES_PER_SCANLINE = 341;
const pixel_coord VISIBLE_COLUMNS = 256;

// visible assuming no scrolling
const int VISIBLE_TILE_ROWS = VISIBLE_SCANLINES/8;
const int VISIBLE_TILE_COLUMNS = VISIBLE_COLUMNS/8;

const pixel_coord SCREEN_WIDTH = VISIBLE_COLUMNS;
const pixel_coord SCREEN_HEIGHT = VISIBLE_SCANLINES;

const int VERTICES_PER_TILE = 6;

// TODO: change to account for differing numbers of nametables
const int N_NAMETABLES = 2;
const int SCROLL_SPACE_SIZE =
  VISIBLE_TILE_ROWS * VISIBLE_TILE_COLUMNS * VERTICES_PER_TILE * N_NAMETABLES;

const int PATTERN_TABLE_TILES = 256;
const int PATTERN_TABLE_LENGTH = PATTERN_TABLE_TILES * 8 * 8;

const GLenum BG_PATTERN_TABLE_TEXTURE = GL_TEXTURE0;
const int BG_PATTERN_TABLE_TEXID = 0;
const GLenum SPRITE_PATTERN_TABLE_TEXTURE = GL_TEXTURE1;
const int SPRITE_PATTERN_TABLE_TEXID = 1;

const int LOCAL_PALETTES_LENGTH = 16*4;

const float FPS_UPDATE_INTERVAL = 2.0; // in seconds
const int MAX_FPS = 60;
const float SECONDS_PER_FRAME = 1.0 / MAX_FPS;

// gain determining seconds per frame (as in a kalman filter)
const float SPF_GAIN = 0.2;

const unsigned char KEY_MASK_A = 1<<0;
const unsigned char KEY_MASK_B = 1<<1;
const unsigned char KEY_MASK_SELECT = 1<<2;
const unsigned char KEY_MASK_START = 1<<3;
const unsigned char KEY_MASK_UP = 1<<4;
const unsigned char KEY_MASK_DOWN = 1<<5;
const unsigned char KEY_MASK_LEFT = 1<<6;
const unsigned char KEY_MASK_RIGHT = 1<<7;

const unsigned char MASK_MASK_GREYSCALE = 1<<0;
const unsigned char MASK_MASK_BKG_LEFT = 1<<1;
const unsigned char MASK_MASK_SPRITE_LEFT = 1<<2;
const unsigned char MASK_MASK_BKG = 1<<3;
const unsigned char MASK_MASK_SPRITE = 1<<4;
const unsigned char MASK_MASK_EMPH_RED = 1<<5;
const unsigned char MASK_MASK_EMPH_GREEN = 1<<6;
const unsigned char MASK_MASK_EMPH_BLUE = 1<<7;

const int DONKEY_KONG_BIG_HEAD_MODE = 0;
const int DONKEY_KONG_BIG_HEAD_INCREASE = 16;

// This needs to match up with the MirrorMode enum in rom.py
enum ScrollType {
  // Note: vertical scrolling means horizontal mirroring, and vice
  // versa
  SCROLL_VERTICAL = 1,   // MirrorMode.horizontalMirroring
  SCROLL_HORIZONTAL = 2, // MirrorMode.verticalMirroring
  SCROLL_BOTH = 3,       // MirrorMode.fourScreenVRAM
  SCROLL_NONE = 4        // MirrorMode.oneScreenMirroring
};

class Screen {
public:
  Screen(ScrollType st);

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
  void setTileIndices(unsigned char *, unsigned int len);
  void setPaletteIndices(vector<vector<unsigned char> >);
  void setPaletteIndices(unsigned char *, unsigned int len);
  void setOam(unsigned char *);
  void setMask(unsigned char);
  void setScrollCoords(unsigned int x, unsigned int y);
  void setScrollType(ScrollType st);

  void testRenderLoop();
  void drawToBuffer();
  int draw();

  unsigned char pollKeys();

private:
  GLFWwindow *window;
  GLuint shader;
  // shader attribute locations
  GLint posAttrib;
  GLint priorityAttrib;
  GLint tileAttrib;
  GLint uvAttrib;
  GLint paletteNAttrib;

  // shader uniform locations
  GLint patternTableUniform;
  GLint localPalettesUniform;

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

  vector<struct glVertex> bgVertices;

  float bgPalettes[LOCAL_PALETTES_LENGTH];

  int universalBg;

  struct oamEntry oam[OAM_ENTRIES];

  vector<struct glVertex> spriteVertices;

  float spritePalettes[LOCAL_PALETTES_LENGTH];

  unsigned char maskState;

  vector<scrollChange> scrollChanges;

  unsigned int scrollX;
  unsigned int scrollY;

  ScrollType scrollType;

  // methods

  void initShaders();
  void setupFrame();

  ntab_coord tileRows();
  ntab_coord tileColumns();
  scroll_coord scrollWidth();
  scroll_coord scrollHeight();

  void drawBg();
  void drawSprites();

  void drawVertices(
    vector<glVertex> &vertices,
    GLuint vbo,
    GLuint ptabName,
    GLenum ptabTex,
    int ptabTexId,
    float *palettes
    );

  void appendRect(
    vector<glVertex> &vertices,
    pixel_coord x_left, pixel_coord x_right,
    pixel_coord y_top, pixel_coord y_bottom,
    float priority,
    ptab_tile_coord tile,
    ptab_uv_coord u_left, ptab_uv_coord u_right,
    ptab_uv_coord v_top, ptab_uv_coord v_bottom,
    unsigned char palette_index
    );

};



int initWindow(GLFWwindow**);

void die();

#endif
