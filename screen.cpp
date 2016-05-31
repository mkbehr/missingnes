#include <cstddef>
#include <iostream>
#include <string>
#include <sstream>
#include <fstream>
#include <cassert>

#include <unistd.h>
#include <sys/param.h>



using namespace std;

#include "screen.hpp"
#include "palette.hpp"

#define INNER_STRINGIZE(x) #x
#define STRINGIZE(x) INNER_STRINGIZE(x)
#define checkGlErrors(cont) \
  (_checkGlErrors(cont, __FILE__ ":" STRINGIZE(__LINE__)))

void die(void) {
  glfwTerminate();
  exit(-1);
}

const char *glErrorString(GLenum err) {
  switch (err) {
  case GL_INVALID_ENUM:
    return "Invalid enum";
  case GL_INVALID_VALUE:
    return "Invalud value";
  case GL_INVALID_OPERATION:
    return "Invalid operation";
  case GL_OUT_OF_MEMORY:
    return "Out of memory";
  case GL_INVALID_FRAMEBUFFER_OPERATION:
    return "Invalid framebuffer operation";
  default:
    return "Unrecognized error";
  }
}

void _checkGlErrors(int continue_after_err,
                    const char *errloc) {
  GLenum err = GL_NO_ERROR;
  while ((err = glGetError()) != GL_NO_ERROR) {
    const char *errMsg = glErrorString(err);
    cerr << errloc
         << ": GL error: " << errMsg
         << " (" << hex << err << ")\n";
    if (!continue_after_err) {
      die();
    }
  }
}

Screen::Screen(void) {

  // Bit of a hack here: initializing the window will change the
  // working directory for some reason, so store it and change it back
  char cwd[MAXPATHLEN];
  if (!getcwd(cwd, MAXPATHLEN)) {
    cerr << "Couldn't get working directory\n";
    die();
  }

  // TODO assign pointer to PPU object (or let python handle that interface)

  if (initWindow(&window) < 0) {
    cerr << "Couldn't create window\n";
    die();
  }

  if (chdir(cwd) != 0) {
    cerr << "Couldn't reset working directory\n";
    die();
  }

  // initWindow also does this check, but let's be safe and make sure
  // the window made it out of initWindow okay
  if (glfwGetWindowAttrib(window, GLFW_CONTEXT_VERSION_MAJOR) < 3) {
    cerr << "Screen: Error: GL major version too low\n";
    die();
  }

  glfwSetInputMode(window, GLFW_STICKY_KEYS, 1);

  // bind a vertex array
  GLuint va;
  glGenVertexArrays(1, &va);
  checkGlErrors(0);
  glBindVertexArray(va);
  checkGlErrors(0);

  initShaders();


  glGenBuffers(1, &bgVbo);
  glGenBuffers(1, &spriteVbo);
  glGenTextures(1, &bgPtabName);
  glGenTextures(1, &spritePtabName);

  checkGlErrors(0);

  lastBgPalette = -1;
  lastSpritePalette = -1;

  glEnable(GL_BLEND);
  glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
  checkGlErrors(0);

  // things to zero-initialize: local palettes, pattern tables, tile
  // indices, palette indices

  // There is a more c++ style way to get the array lengths here. Eh.
  memset(bgPalettes, 0, LOCAL_PALETTES_LENGTH * sizeof(float));
  memset(spritePalettes, 0, LOCAL_PALETTES_LENGTH * sizeof(float));
  memset(oam, 0, OAM_SIZE);

  vector<float> zeroPtab(PATTERN_TABLE_LENGTH, 0);
  setBgPatternTable(zeroPtab);
  setSpritePatternTable(zeroPtab);

  // set up state

  initBgVertices();

  // there's probably a cleaner c++ way to do this
  tileIndices.resize(TILE_COLUMNS);
  paletteIndices.resize(TILE_COLUMNS);
  for (int i = 0; i < TILE_COLUMNS; i++) {
    tileIndices[i].resize(TILE_ROWS);
    paletteIndices[i].resize(TILE_ROWS);
  }

  setUniversalBg(0);

  spriteVertices.reserve(OAM_ENTRIES * 6);
}

GLint safeGetAttribLocation(GLuint program, const GLchar *name) {
  GLint loc = glGetAttribLocation(program, name);
  checkGlErrors(0);
  if (loc < 0) {
    cerr << "Couldn't get program attribute " << name << "\n";
    die();
  }
  return loc;
}

// doesn't return an error message, just exits the program on error
void Screen::initShaders(void) {
  // get shaders
  ifstream vertFile(VERTEX_SHADER_FILE);
  if (!vertFile) {
    cerr << "Couldn't open vertex shader file\n";
    die();
  }
  stringstream vertBuffer;
  vertBuffer << vertFile.rdbuf();
  // This approach makes the string turn into the empty string for some reason
  // const char *vertSrc = vertBuffer.str().c_str();
  string vertStr = vertBuffer.str();
  const char *vertSrc = vertStr.c_str();
  // TODO error-check and make sure the file isn't too big
  int vertSrcLen = (int) vertStr.length();
  ifstream fragFile(FRAGMENT_SHADER_FILE);
  if (!fragFile) {
    cerr << "Couldn't open fragment shader file\n";
    die();
  }
  stringstream fragBuffer;
  fragBuffer << fragFile.rdbuf();
  string fragStr = fragBuffer.str();
  const char *fragSrc = fragStr.c_str();
  int fragSrcLen = (int) fragStr.length();


  // compile shaders
  GLuint vertexShader = glCreateShader(GL_VERTEX_SHADER);
  glShaderSource(vertexShader, 1, &vertSrc, &vertSrcLen);
  glCompileShader(vertexShader);
  // check compilation
  GLint status;
  glGetShaderiv(vertexShader, GL_COMPILE_STATUS, &status);
  if (!status) {
    cerr << "Error compiling vertex shader:\n";
    GLint logLen = 0;
    glGetShaderiv(vertexShader, GL_INFO_LOG_LENGTH, &logLen);
    if (logLen > 1) {
      GLchar *log = (GLchar*) malloc(logLen);
      GLint readLogLen = 0;
      glGetShaderInfoLog(vertexShader, logLen, &readLogLen, log);
      // FIXME should probably only print logLen chars here just to be safe
      cout << log;
    } else {
      cerr << "Couldn't get log message\n";
    }
    die();
  }

  GLuint fragmentShader = glCreateShader(GL_FRAGMENT_SHADER);
  glShaderSource(fragmentShader, 1, &fragSrc, &fragSrcLen);
  glCompileShader(fragmentShader);
  glGetShaderiv(fragmentShader, GL_COMPILE_STATUS, &status);
  if (!status) {
    cerr << "Error compiling fragment shader:\n";
    GLint logLen = 0;
    glGetShaderiv(fragmentShader, GL_INFO_LOG_LENGTH, &logLen);
    if (logLen > 1) {
      GLchar *log = (GLchar*) malloc(logLen);
      GLint readLogLen = 0;
      glGetShaderInfoLog(fragmentShader, logLen, &readLogLen, log);
      // FIXME should probably only print logLen chars here just to be safe
      cout << log;
    } else {
      cerr << "Couldn't get log message\n";
    }
    die();
  }

  // link shader program
  shader = glCreateProgram();
  glAttachShader(shader, vertexShader);
  glAttachShader(shader, fragmentShader);
  glLinkProgram(shader);

  glGetProgramiv(shader, GL_LINK_STATUS, &status);
  if (!status) {
    cerr << "Error linking shader:\n";
    GLint logLen = 0;
    glGetProgramiv(shader, GL_INFO_LOG_LENGTH, &logLen);
    if (logLen > 1) {
      GLchar *log = (GLchar*) malloc(logLen);
      GLint readLogLen = 0;
      glGetProgramInfoLog(shader, logLen, &readLogLen, log);
      // FIXME should probably only print logLen chars here just to be safe
      cout << log;
    } else {
      cerr << "Couldn't get log message\n";
    }
    die();
  }

  glUseProgram(shader);
  checkGlErrors(0);

  // shader attribute pointers
  xyAttrib = safeGetAttribLocation(shader, "xy");
  xHighAttrib = safeGetAttribLocation(shader, "x_high");
  tuvAttrib = safeGetAttribLocation(shader, "v_tuv");
  paletteNAttrib = safeGetAttribLocation(shader, "v_palette_n");
}

void Screen::initBgVertices(void) {
  for (int x = 0; x < TILE_COLUMNS; x++) {
    unsigned char x_left = x*8;
    unsigned char x_right = (x+1)*8;
    unsigned char x_left_high = 0;
    unsigned char x_right_high = (x_right == 0 ? 1 : 0);
    for (int y = 0; y < TILE_ROWS; y++) {
      unsigned char y_bottom = (TILE_ROWS - y - 1) * 8;
      unsigned char y_top = (TILE_ROWS - y) * 8;
      unsigned char tile = 0; // this will change
      unsigned char u_left = 0;
      unsigned char u_right = 1;
      unsigned char v_bottom = 1;
      unsigned char v_top = 0;
      unsigned char palette_index = 0; // this will change

      int vertex_index =
        (x + y*TILE_COLUMNS) * VERTICES_PER_TILE;

      struct glVertex bottomLeft =
        {x_left, y_bottom, x_left_high,
         tile, u_left, v_bottom, palette_index};
      struct glVertex bottomRight =
        {x_right, y_bottom, x_right_high,
         tile, u_right, v_bottom, palette_index};
      struct glVertex topLeft =
        {x_left, y_top, x_left_high,
         tile, u_left, v_top, palette_index};
      struct glVertex topRight =
        {x_right, y_top, x_right_high,
         tile, u_right, v_top, palette_index};

      // represent square as two triangles
      // first triangle
      bgVertices[vertex_index] = bottomLeft;
      bgVertices[vertex_index+1] = bottomRight;
      bgVertices[vertex_index+2] = topRight;
      // second triangle
      bgVertices[vertex_index+3] = bottomLeft;
      bgVertices[vertex_index+4] = topRight;
      bgVertices[vertex_index+5] = topLeft;
      // TODO: look into using point sprites instead of triangles
    }
  }
}

void Screen::setUniversalBg(int bg) {
  // TODO check that this is a valid index into PALETTE
  universalBg = bg;
}

void Screen::setBgPalettes(vector<float> localPaletteInput) {
  assert(localPaletteInput.size() == LOCAL_PALETTES_LENGTH);
  memcpy(bgPalettes, localPaletteInput.data(),
         LOCAL_PALETTES_LENGTH * sizeof(float));
}

// Assumes that the input is exactly LOCAL_PALETTES_LENGTH long
void Screen::setBgPalettes(float *localPaletteInput) {
  memcpy(bgPalettes, localPaletteInput,
         LOCAL_PALETTES_LENGTH * sizeof(float));
}

void Screen::setSpritePalettes(vector<float> localPaletteInput) {
  assert(localPaletteInput.size() == LOCAL_PALETTES_LENGTH);
  memcpy(spritePalettes, localPaletteInput.data(),
         LOCAL_PALETTES_LENGTH * sizeof(float));
}

// Assumes that the input is exactly LOCAL_PALETTES_LENGTH long
void Screen::setSpritePalettes(float *localPaletteInput) {
  memcpy(spritePalettes, localPaletteInput,
         LOCAL_PALETTES_LENGTH * sizeof(float));
}

void Screen::setTileIndices(vector<vector<unsigned char> > tiles) {
  tileIndices = tiles;
}

void Screen::setTileIndices(unsigned char *tiles) {
  // this is probably slower than it needs to be, but let's just make
  // it work for now
  tileIndices.resize(TILE_COLUMNS);
  for (int x = 0; x < TILE_COLUMNS; x++) {
    tileIndices[x].resize(TILE_ROWS);
    for (int y = 0; y < TILE_ROWS; y++) {
      tileIndices[x][y] = tiles[(x * TILE_ROWS) + y];
    }
  }
}

void Screen::setPaletteIndices(vector<vector<unsigned char> > palettes) {
  paletteIndices = palettes;
}

void Screen::setPaletteIndices(unsigned char *indices) {
  // this is probably slower than it needs to be, but let's just make
  // it work for now
  paletteIndices.resize(TILE_COLUMNS);
  for (int x = 0; x < TILE_COLUMNS; x++) {
    paletteIndices[x].resize(TILE_ROWS);
    for (int y = 0; y < TILE_ROWS; y++) {
      paletteIndices[x][y] = indices[(x * TILE_ROWS) + y];
    }
  }
}

// assume the size is equal to 8*8*PATTERN_TABLE_TILES (TODO fix magic number)
void Screen::setBgPatternTable(float *bgPtabInput) {
  glBindBuffer(GL_ARRAY_BUFFER, bgVbo);
  glActiveTexture(BG_PATTERN_TABLE_TEXTURE);
  glBindTexture(GL_TEXTURE_2D, bgPtabName);
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, 8*PATTERN_TABLE_TILES, 8,
               0, GL_RED, GL_FLOAT, bgPtabInput);
  checkGlErrors(0);
}

void Screen::setBgPatternTable(vector<float> bgPtabInput) {
  /* Note: according to stackoverflow, glTexImage2D allows the memory
     to be freed after the call, so I don't have to worry about
     copying the input over to somewhere stable. I can't find the part
     of the API that actually says that, but for now I'll trust it.

     http://stackoverflow.com/questions/26499361/opengl-what-does-glteximage2d-do
  */

  // TODO fix magic number
  assert(bgPtabInput.size() == 8*8*PATTERN_TABLE_TILES);
  setBgPatternTable(bgPtabInput.data());
}

void Screen::setSpritePatternTable(float *spritePtabInput) {
  glBindBuffer(GL_ARRAY_BUFFER, spriteVbo);
  glActiveTexture(SPRITE_PATTERN_TABLE_TEXTURE);
  glBindTexture(GL_TEXTURE_2D, spritePtabName);
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, 8*PATTERN_TABLE_TILES, 8,
               0, GL_RED, GL_FLOAT, spritePtabInput);
  checkGlErrors(0);
}

void Screen::setSpritePatternTable(vector<float> spritePtabInput) {
  assert(spritePtabInput.size() == 8*8*PATTERN_TABLE_TILES);
  setSpritePatternTable(spritePtabInput.data());
}

void Screen::setOam(unsigned char *oamBytes) {
  // Not bothering to write the struct interface, because we'll only
  // actually use this by taking byte-array input from the NES.
  memcpy(oam, oamBytes, OAM_SIZE);
}


void Screen::drawToBuffer() {
  // State we need by the time we finish this:
  // For all:
  // - universalBg needs to be set to the universal background palette index
  // For background:
  // - bgPalettes needs to be set to a buffer with the local palettes
  // - BG_PATTERN_TABLE_TEXTURE needs to be populated with the background pattern table
  // - we need data for the actual tiles (tileIndices and paletteIndices from the python, set by the ppu)
  //   (so maybe keep the ppu setting that, and then move it from python to c++)
  // For sprites:
  // - spritePalettes needs to be set to a buffer with the local palettes
  // - SPRITE_PATTERN_TABLE_TEXTURE needs to be poulated with the sprite pattern table
  // - oam needs to be set to the OAM contents

  assert(universalBg < N_PALETTES);
  unsigned char *bgPalette = PALETTE[universalBg];
  glClearColor(((float) bgPalette[0]) / 255.0,
               ((float) bgPalette[1]) / 255.0,
               ((float) bgPalette[2]) / 255.0,
               1.0);
  glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

  if (DRAW_BG) {
    glBindBuffer(GL_ARRAY_BUFFER, bgVbo);

    // From python implementation comments:
    // We need to do this here (anytime before the draw call) and I
    // don't understand why. The order is important for some reason.
    glActiveTexture(BG_PATTERN_TABLE_TEXTURE);
    glBindTexture(GL_TEXTURE_2D, bgPtabName);

    // do we need to call these again? unclear. python code did it but
    // I don't know why.
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

    checkGlErrors(0);

    // Set tile and palette. The rest of the values in the VBO won't change.
    for (int x = 0; x < TILE_COLUMNS; x++) {
      for (int y = 0; y < TILE_ROWS; y++) {
        unsigned char tile = tileIndices[x][y];
        unsigned char palette = paletteIndices[x][y];
        int screen_tile_index = (x + y*TILE_COLUMNS) * VERTICES_PER_TILE;
        for (int vertex_i = 0; vertex_i < VERTICES_PER_TILE; vertex_i++) {
          bgVertices[screen_tile_index + vertex_i].tile = tile;
          bgVertices[screen_tile_index + vertex_i].palette = palette;
        }
      }
    }

    int stride = sizeof(struct glVertex);
    glBufferData(GL_ARRAY_BUFFER, N_BG_VERTICES * sizeof(struct glVertex),
                 bgVertices, GL_DYNAMIC_DRAW);
    checkGlErrors(0);
    glVertexAttribPointer(xyAttrib, 2, GL_UNSIGNED_BYTE, GL_FALSE, stride,
                          (const GLvoid *) offsetof(struct glVertex, x_low));
    glEnableVertexAttribArray(xyAttrib);
    checkGlErrors(0);
    glVertexAttribPointer(xHighAttrib, 1, GL_UNSIGNED_BYTE, GL_FALSE, stride,
                          (const GLvoid *) offsetof(struct glVertex, x_high));
    glEnableVertexAttribArray(xHighAttrib);
    checkGlErrors(0);
    glVertexAttribPointer(tuvAttrib, 3, GL_UNSIGNED_BYTE, GL_FALSE, stride,
                          (const GLvoid *) offsetof(struct glVertex, tile));
    glEnableVertexAttribArray(tuvAttrib);
    checkGlErrors(0);
    glVertexAttribPointer(paletteNAttrib, 1, GL_UNSIGNED_BYTE, GL_FALSE, stride,
                          (const GLvoid *) offsetof(struct glVertex, palette));
    glEnableVertexAttribArray(paletteNAttrib);
    checkGlErrors(0);

    glUniform1i(glGetUniformLocation(shader, "patternTable"),
                BG_PATTERN_TABLE_TEXID);
    checkGlErrors(0);

    // FIXME magic number 16
    glUniform4fv(glGetUniformLocation(shader, "localPalettes"), 16,
                 bgPalettes);
    checkGlErrors(0);

    glDrawArrays(GL_TRIANGLES, 0, N_BG_VERTICES);
    checkGlErrors(0);
  }
  if (DRAW_SPRITES) {
    glBindBuffer(GL_ARRAY_BUFFER, spriteVbo);

    glActiveTexture(SPRITE_PATTERN_TABLE_TEXTURE);
    glBindTexture(GL_TEXTURE_2D, spritePtabName);

    // still don't remember why/whether these glTexParameteri calls
    // are necessary
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

    spriteVertices.resize(0);

    for (int oam_i = 0; oam_i < OAM_ENTRIES; oam_i++) {
      // TODO deal with maximum sprites per scanline
      struct oamEntry sprite = oam[oam_i];
      if (sprite.y_minus_one >= 0xef) {
          // The sprite is wholly off the screen; ignore it
          continue;
        }
      // preceding check ensures this won't overflow
      unsigned char spritetop = sprite.y_minus_one + 1;

      unsigned char x_left = sprite.x;
      unsigned char x_left_high = 0;
      unsigned char x_right = sprite.x + 8;
      unsigned char x_right_high = (x_right < 8 ? 1 : 0);

      unsigned char y_top = SCREEN_HEIGHT - sprite.y_minus_one - 1;
      unsigned char y_bottom = y_top - 8;

      unsigned char u_left =
        (sprite.attributes & OAM_FLIP_HORIZONTAL ? 1 : 0);
      unsigned char u_right = 1 - u_left;

      unsigned char v_top =
        (sprite.attributes & OAM_FLIP_VERTICAL ? 1 : 0);
      unsigned char v_bottom = 1 - v_top;

      unsigned char tile = sprite.tile;
      unsigned char palette_index = (sprite.attributes & OAM_PALETTE);

      if (DONKEY_KONG_BIG_HEAD_MODE) {
        // The main head tiles seem to be the even-numbered tiles in
        // the first 4 rows of 16 tiles each. (There are more for
        // various special states but I'll ignore them.)
        if ((tile < 0x40) && ((tile % 2) == 0)) {
          // I forgot to check for overflow here but the result is
          // hilarious so I'm gonna leave it in
	  y_top += DONKEY_KONG_BIG_HEAD_INCREASE;
	  // The back-of-head tiles seem to be at multiples of 4, and
	  // the front-of-head tiles are at 2 plus a multiple of 4.
	  // They're all facing to the right.
	  int is_head_front = (tile % 4);
	  // Stretch front head to the right and back head to the
	  // left, unless it's horizontally mirrored.
          if ((!!is_head_front) != (!!(sprite.attributes & OAM_FLIP_HORIZONTAL))) {
            x_right += DONKEY_KONG_BIG_HEAD_INCREASE;
            x_right_high = (x_right < (DONKEY_KONG_BIG_HEAD_INCREASE + 8) ? 1 : 0);
	  } else {
	    if (x_left <= DONKEY_KONG_BIG_HEAD_INCREASE) {
	      x_left = 0;
	    } else {
	      x_left -= DONKEY_KONG_BIG_HEAD_INCREASE;
	    }
	  }
	}
      }

      struct glVertex bottomLeft =
        {x_left, y_bottom, x_left_high,
         tile, u_left, v_bottom, palette_index};
      struct glVertex bottomRight =
        {x_right, y_bottom, x_right_high,
         tile, u_right, v_bottom, palette_index};
      struct glVertex topLeft =
        {x_left, y_top, x_left_high,
         tile, u_left, v_top, palette_index};
      struct glVertex topRight =
        {x_right, y_top, x_right_high,
         tile, u_right, v_top, palette_index};

      // first triangle
      spriteVertices.push_back(bottomLeft);
      spriteVertices.push_back(bottomRight);
      spriteVertices.push_back(topRight);
      // second triangle
      spriteVertices.push_back(bottomLeft);
      spriteVertices.push_back(topRight);
      spriteVertices.push_back(topLeft);
    }
    // Not sure whether or not this code all needs to be repeated -
    // it's mostly the same as the bg code. Only differences are
    // pattern table, palettes, and number of vertices drawn.
    int stride = sizeof(struct glVertex);
    glBufferData(GL_ARRAY_BUFFER, spriteVertices.size() * sizeof(struct glVertex),
                 spriteVertices.data(), GL_DYNAMIC_DRAW);
    checkGlErrors(0);
    glVertexAttribPointer(xyAttrib, 2, GL_UNSIGNED_BYTE, GL_FALSE, stride,
                          (const GLvoid *) offsetof(struct glVertex, x_low));
    glEnableVertexAttribArray(xyAttrib);
    checkGlErrors(0);
    glVertexAttribPointer(xHighAttrib, 1, GL_UNSIGNED_BYTE, GL_FALSE, stride,
                          (const GLvoid *) offsetof(struct glVertex, x_high));
    glEnableVertexAttribArray(xHighAttrib);
    checkGlErrors(0);
    glVertexAttribPointer(tuvAttrib, 3, GL_UNSIGNED_BYTE, GL_FALSE, stride,
                          (const GLvoid *) offsetof(struct glVertex, tile));
    glEnableVertexAttribArray(tuvAttrib);
    checkGlErrors(0);
    glVertexAttribPointer(paletteNAttrib, 1, GL_UNSIGNED_BYTE, GL_FALSE, stride,
                          (const GLvoid *) offsetof(struct glVertex, palette));
    glEnableVertexAttribArray(paletteNAttrib);
    checkGlErrors(0);

    glUniform1i(glGetUniformLocation(shader, "patternTable"),
                SPRITE_PATTERN_TABLE_TEXID);
    checkGlErrors(0);

    // FIXME magic number 16
    glUniform4fv(glGetUniformLocation(shader, "localPalettes"), 16,
                 spritePalettes);
    checkGlErrors(0);

    glDrawArrays(GL_TRIANGLES, 0, spriteVertices.size());
    checkGlErrors(0);
  }
}

int Screen::draw() {
  glfwSwapBuffers(window);
  glfwPollEvents();
  if (glfwWindowShouldClose(window)) {
    glfwTerminate();
    return 1;
  }
  return 0;
}

// Polls for keys, returns their state in a one-byte bitfield (masks
// defined in header)
unsigned char Screen::pollKeys() {
  // Currently, we're polling events here and in draw(). Is that a
  // problem? Not sure.
  glfwPollEvents();
  // TODO check to make sure we've set GLFW_STICKY_KEYS
  unsigned char out = 0;
  if (glfwGetKey(window, GLFW_KEY_A) == GLFW_PRESS) {
    out |= KEY_MASK_A;
  }
  if (glfwGetKey(window, GLFW_KEY_S) == GLFW_PRESS) {
    out |= KEY_MASK_B;
  }
  if (glfwGetKey(window, GLFW_KEY_BACKSLASH) == GLFW_PRESS) {
    out |= KEY_MASK_SELECT;
  }
  if (glfwGetKey(window, GLFW_KEY_ENTER) == GLFW_PRESS) {
    out |= KEY_MASK_START;
  }
  if (glfwGetKey(window, GLFW_KEY_UP) == GLFW_PRESS) {
    out |= KEY_MASK_UP;
  }
  if (glfwGetKey(window, GLFW_KEY_DOWN) == GLFW_PRESS) {
    out |= KEY_MASK_DOWN;
  }
  if (glfwGetKey(window, GLFW_KEY_LEFT) == GLFW_PRESS) {
    out |= KEY_MASK_LEFT;
  }
  if (glfwGetKey(window, GLFW_KEY_RIGHT) == GLFW_PRESS) {
    out |= KEY_MASK_RIGHT;
  }
  return out;
}


int initWindow(GLFWwindow **window_p) {
  /* Initialize the library */
  if (!glfwInit()) {
    cerr << "glfwInit failed\n";
    return -1;
  }

  glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
  glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 2);
  glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE);
  glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

  /* Create a windowed mode window and its OpenGL context */
  GLFWwindow *window;
  window = glfwCreateWindow(SCREEN_WIDTH, SCREEN_HEIGHT,
                            PROGRAM_NAME, NULL, NULL);
  if (!window)
    {
      cerr << "glfwCreateWindow failed\n";
      glfwTerminate();
      return -1;
    }

  if (glfwGetWindowAttrib(window, GLFW_CONTEXT_VERSION_MAJOR) < 3) {
    cerr << "initWindow: Error: GL major version too low\n";
    die();
  }

  /* Make the window's context current */
  glfwMakeContextCurrent(window);

  *window_p = window;
  return 0;
}

void Screen::testRenderLoop(void) {

  /* Loop until the user closes the window */
  while (!glfwWindowShouldClose(window))
  {
    drawToBuffer();

    /* Swap front and back buffers */
    glfwSwapBuffers(window);

    /* Poll for and process events */
    glfwPollEvents();
  }

  glfwTerminate();
}

// ctypes interface

extern "C" {

  Screen *ex_constructScreen(void) {
    return new Screen();
  }

  void ex_setUniversalBg(Screen *sc, int bg) {
    sc->setUniversalBg(bg);
  }

  // localPaletteInput must point to an array of exactly
  // LOCAL_PALETTES_LENGTH elements. I don't check this here because
  // FFIs are hard, but the python interface does check.
  void ex_setBgPalettes(Screen *sc, float *localPaletteInput) {
    sc->setBgPalettes(localPaletteInput);
  }

  void ex_setSpritePalettes(Screen *sc, float *localPaletteInput) {
    sc->setSpritePalettes(localPaletteInput);
  }

  void ex_setBgPatternTable(Screen *sc, float *ptab) {
    sc->setBgPatternTable(ptab);
  }

  void ex_setSpritePatternTable(Screen *sc, float *ptab) {
    sc->setSpritePatternTable(ptab);
  }

  void ex_setTileIndices(Screen *sc, unsigned char *indices) {
    sc->setTileIndices(indices);
  }

  void ex_setPaletteIndices(Screen *sc, unsigned char *indices) {
    sc->setPaletteIndices(indices);
  }

  void ex_setOam(Screen *sc, unsigned char *oamBytes) {
    sc->setOam(oamBytes);
  }

  void ex_drawToBuffer(Screen *sc) {
    sc->drawToBuffer();
  }

  int ex_draw(Screen *sc) {
    return sc->draw();
  }

  unsigned char ex_pollKeys(Screen *sc) {
    return sc->pollKeys();
  }

}
