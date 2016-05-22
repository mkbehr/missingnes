#include <GLFW/glfw3.h>

class Screen {
 public:
  Screen();

 private:
  GLFWwindow *window;
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


  // PPU state trackers
  int lastBgPalette;
  int lastSpritePalette;
  // TODO tileIndices, paletteIndices, bgVertices

  void initShaders();
};

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

const int N_BG_VERTICES = TILE_ROWS * TILE_COLUMNS * 6;

const int PATTERN_TABLE_TILES = 256;

const GLenum BG_PATTERN_TABLE_TEXTURE = GL_TEXTURE0;
const int BG_PATTERN_TABLE_TEXID = 0;
const GLenum SPRITE_PATTERN_TABLE_TEXTURE = GL_TEXTURE1;
const int SPRITE_PATTERN_TABLE_TEXID = 1;
// TODO other texture ids go here

// number of values (elements) per vertex in the vertex buffer
const int VERTEX_ELTS = 7;

const int DRAW_BG = 1;
const int DRAW_SPRITES = 1;

const float FPS_UPDATE_INTERVAL = 2.0; // in seconds
const int MAX_FPS = 60;
const float SECONDS_PER_FRAME = 1.0 / MAX_FPS;

// gain determining seconds per frame (as in a kalman filter)
const float SPF_GAIN = 0.2;

int initWindow(GLFWwindow**);

void die();
