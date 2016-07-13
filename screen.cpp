#include <cstddef>
#include <iostream>
#include <string>
#include <sstream>
#include <fstream>
#include <cassert>
#include <stdnoreturn.h>

#include <unistd.h>
#include <sys/param.h>



using namespace std;

#include "screen.hpp"
#include "palette.hpp"

#define INNER_STRINGIZE(x) #x
#define STRINGIZE(x) INNER_STRINGIZE(x)
#define checkGlErrors(cont) \
  (_checkGlErrors(cont, __FILE__ ":" STRINGIZE(__LINE__)))

noreturn void die(void) {
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

Screen::Screen(ScrollType st)
  : scrollType(st), scrollX(0), scrollY(0)
{
  // Bit of a hack here: initializing the window will change the
  // working directory for some reason, so store it and change it back
  char cwd[MAXPATHLEN];
  if (!getcwd(cwd, MAXPATHLEN)) {
    cerr << "Couldn't get working directory\n";
    die();
  }

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

  setupFrame();

  // there's probably a cleaner c++ way to do this
  tileIndices.resize(tileColumns());
  paletteIndices.resize(tileColumns());
  for (int i = 0; i < tileColumns(); i++) {
    tileIndices[i].resize(tileRows());
    paletteIndices[i].resize(tileRows());
  }

  setUniversalBg(0);

  spriteVertices.reserve(OAM_ENTRIES * 6);
}

ntab_coord Screen::tileRows() {
  switch(scrollType) {
  case SCROLL_VERTICAL:
    return VISIBLE_TILE_ROWS * 2;
  case SCROLL_HORIZONTAL:
    return VISIBLE_TILE_ROWS;
  default:
    cerr << "tileRows: invalid scroll type\n";
    die();
  }
}

ntab_coord Screen::tileColumns() {
  switch(scrollType) {
  case SCROLL_VERTICAL:
    return VISIBLE_TILE_COLUMNS;
  case SCROLL_HORIZONTAL:
    return VISIBLE_TILE_COLUMNS * 2;
  default:
    cerr << "tileColumns: invalid scroll type\n";
    die();
  }
}

scroll_coord Screen::scrollWidth() {
  return (scroll_coord) (tileColumns() * 8);
}

scroll_coord Screen::scrollHeight() {
  return (scroll_coord) (tileRows() * 8);
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

GLint safeGetUniformLocation(GLuint program, const GLchar *name) {
  GLint loc = glGetUniformLocation(program, name);
  checkGlErrors(0);
  if (loc < 0) {
    cerr << "Couldn't get program uniform " << name << "\n";
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

  // shader attribute/uniform pointers
  posAttrib = safeGetAttribLocation(shader, "pos");
  priorityAttrib = safeGetAttribLocation(shader, "priority");
  tileAttrib = safeGetAttribLocation(shader, "tile");
  uvAttrib = safeGetAttribLocation(shader, "v_uv");
  paletteNAttrib = safeGetAttribLocation(shader, "v_palette_n");

  patternTableUniform = safeGetUniformLocation(shader, "patternTable");
  localPalettesUniform = safeGetUniformLocation(shader, "localPalettes");
}

void Screen::setupFrame() {
  // initialize scroll-changes vector
  scrollChanges.clear();
  scrollChange topLeftScrollChange =
    { (scroll_coord) scrollX, (scroll_coord) scrollY,
      0, 0 };
  scrollChanges.push_back(topLeftScrollChange);
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

void Screen::setTileIndices(unsigned char *tiles, unsigned int len) {
  // this is probably slower than it needs to be, but let's just make
  // it work for now
  assert(len == tileColumns() * tileRows());
  tileIndices.resize(tileColumns());
  for (int x = 0; x < tileColumns(); x++) {
    tileIndices[x].resize(tileRows());
    for (int y = 0; y < tileRows(); y++) {
      tileIndices[x][y] = tiles[(x * tileRows()) + y];
    }
  }
}

void Screen::setPaletteIndices(vector<vector<unsigned char> > palettes) {
  paletteIndices = palettes;
}

void Screen::setPaletteIndices(unsigned char *indices, unsigned int len) {
  // this is probably slower than it needs to be, but let's just make
  // it work for now
  assert(len == tileColumns() * tileRows());
  paletteIndices.resize(tileColumns());
  for (int x = 0; x < tileColumns(); x++) {
    paletteIndices[x].resize(tileRows());
    for (int y = 0; y < tileRows(); y++) {
      paletteIndices[x][y] = indices[(x * tileRows()) + y];
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

void Screen::setMask(unsigned char m) {
  maskState = m;
}

void Screen::setScrollCoords(unsigned int x, unsigned int y) {
  scrollX = x;
  scrollY = y;
}

void Screen::setScrollType(ScrollType st) {
  cerr << "Changing scroll types is not implemented\n";
  die();
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
  // - scroll coordinates need to be set (currently assuming they're consistent in a frame)
  // For sprites:
  // - spritePalettes needs to be set to a buffer with the local palettes
  // - SPRITE_PATTERN_TABLE_TEXTURE needs to be poulated with the sprite pattern table
  // - oam needs to be set to the OAM contents

  assert(universalBg < N_PALETTES);
  // Do not confuse universalBgPalette with bgPalettes!
  // universalBgPalette refers to the single background color, and
  // bgPalettes refers to the set of background tiles that make up a
  // lot of our rendering.
  unsigned char *universalBgPalette = PALETTE[universalBg];
  glClearColor(((float) universalBgPalette[0]) / 255.0,
               ((float) universalBgPalette[1]) / 255.0,
               ((float) universalBgPalette[2]) / 255.0,
               1.0);
  glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

  if (maskState & MASK_MASK_BKG) {
    drawBg();
  }
  if (maskState & MASK_MASK_SPRITE) {
    drawSprites();
  }
  // Drawing is done. Now set up the next frame.

  // TODO: This isn't the right place to do the work that this
  // function does. It currently depends on the scroll position at the
  // start of the frame.

  setupFrame();
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

/*
 * So for accurate behavior, our background drawing will actually have
 * to work something like this:
 *
 * - First of all, we throw away our assumption that we have a fixed
 *   number of tiles we're drawing to opengl. That won't be a problem,
 *   just track things in a vector.
 *
 * - We simulate scanning across the image, pixel by pixel. (Of
 *   course, we'll optimize this so we don't actually spend time
 *   thinking about every pixel on the screen)
 *
 * - For every pixel, if we haven't drawn a tile to cover it, we'll
 *   draw the appropriate tile. Depending on the scroll coordinates,
 *   the top-left of the tile will either be exactly on that pixel, or
 *   up to 7 tiles above and/or to the left of it.
 *
 * - We will also track a list of changes to the scroll variables.
 *   When we hit a change, we'll have to render new tiles for every
 *   subsequent pixel. This may involve rendering only part of a tile,
 *   in case e.g. we start drawing halfway down a tile. We can do that
 *   by drawing a rectangle and changing the uv coordinates
 *   correspondingly. For every change we hit, we'll increment a
 *   z-coordinate so that the new tiles overlap the old ones.
 */

void Screen::drawVertices(
  vector<glVertex> &vertices,
  GLuint vbo,
  GLuint ptabName,
  GLenum ptabTex,
  int ptabTexId,
  float *palettes
  ) {

  glBindBuffer(GL_ARRAY_BUFFER, vbo);

  // From python implementation comments:
  // We need to do this here (anytime before the draw call) and I
  // don't understand why. The order is important for some reason.
  glActiveTexture(ptabTex);
  glBindTexture(GL_TEXTURE_2D, ptabName);

  // do we need to call these again? unclear. python code did it but
  // I don't know why.
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

  checkGlErrors(0);

  int stride = sizeof(glVertex);
  glBufferData(GL_ARRAY_BUFFER, vertices.size() * sizeof(glVertex),
               vertices.data(), GL_DYNAMIC_DRAW);
  checkGlErrors(0);
  glVertexAttribPointer(posAttrib, 2, GL_PIXEL_COORD, GL_FALSE, stride,
                        (const GLvoid *) offsetof(glVertex, x_pos));
  glEnableVertexAttribArray(posAttrib);
  checkGlErrors(0);
  glVertexAttribPointer(priorityAttrib, 1, GL_FLOAT, GL_FALSE, stride,
                        (const GLvoid *) offsetof(glVertex, priority));
  glEnableVertexAttribArray(priorityAttrib);
  checkGlErrors(0);
  glVertexAttribPointer(tileAttrib, 1, GL_PTAB_TILE_COORD, GL_FALSE, stride,
                        (const GLvoid *) offsetof(glVertex, tile));
  glEnableVertexAttribArray(tileAttrib);
  checkGlErrors(0);
  glVertexAttribPointer(uvAttrib, 2, GL_PTAB_UV_COORD, GL_FALSE, stride,
                        (const GLvoid *) offsetof(glVertex, u));
  glEnableVertexAttribArray(uvAttrib);
  checkGlErrors(0);
  glVertexAttribPointer(paletteNAttrib, 1, GL_UNSIGNED_BYTE, GL_FALSE, stride,
                        (const GLvoid *) offsetof(glVertex, palette));
  glEnableVertexAttribArray(paletteNAttrib);
  checkGlErrors(0);

  glUniform1i(patternTableUniform, ptabTexId);
  checkGlErrors(0);

  // FIXME magic number 16
  glUniform4fv(localPalettesUniform, 16, palettes);
  checkGlErrors(0);

  glDrawArrays(GL_TRIANGLES, 0, vertices.size());
  checkGlErrors(0);
}

void Screen::drawBg() {

  /*
   * Over the course of rendering, we'll need to transform between
   * several different coordinate spaces. I'll give them some names
   * here.
   *
   * /Pattern table space/ represents the contents of the NES's
   * pattern tables, which store the images to be displayed for each
   * tile. We represent pattern tables with three dimensions: the tile
   * coordinate distinguishes between entries in a pattern table, and
   * the u and v coordinates correspond to the horizontal and vertical
   * location within a tile. The fragment shader does the job of
   * converting coordinates in this space to actual colors.
   *
   * /Pixel space/ represents the NES's screen in pixel units. It
   * ranges from (x = 0, y = 0) to (x = 256, y = 240).
   *
   * /Scroll space/ represents the image before scrolling is applied.
   * Each of its dimensions is either equal to the corresponding pixel
   * space dimension or double the corresponding dimension. Scroll
   * space is toroidal: scrolling off the left of scroll space takes a
   * tile to the right, and scrolling off the bottom takes it to the
   * top.
   *
   * A /scroll region/ is a mapping between a region of pixel space
   * and a region of scroll space. It's specified by three
   * coordinates: a start coordinate in pixel space, an end coordinate
   * in pixel space, and an offset coordinate in scroll space. We have
   * (ssCoord = psCoord + ssOffset). Scroll regions aren't
   * rectangular: they represent regions of time as the PPU sweeps
   * across pixels, so they wrap around scanlines. For example, if a
   * scroll region started 3/4 of the way through scanline 1 and ended
   * 1/4 of the way through scanline 3, it would contain the last 1/4
   * of scanline 1, all of scanline 2, and the first 1/4 of scanline
   * 3:
   *
   *   ..................++++++
   *   ++++++++++++++++++++++++
   *   ++++++..................
   *
   * /Nametable space/ is scroll space, but represented in tiles
   * instead of pixels.
   *
   * /GL space/ is the coordinate space of the screen as OpenGL
   * represents it after the vertex shader. The vertex shader is in
   * charge of converting from pixel space to GL space; we don't need
   * to worry about it anywhere else.
   *
   *
   *
   * So the way background rendering works is as follows:
   *
   * 1. Divide pixel space into scroll regions.
   *
   * 2. For each scroll region, look at the corresponding area in
   * scroll space, and look at the tile boundaries, between the
   * corresponding tiles in nametable space. Create one pixel-space
   * rectangle in the vertex vector (six vertices) for each tile. Clip
   * the rectangles on the top and left; don't bother for the bottom
   * and right. For the tile containing the start of the scroll
   * region, we may need to make two rectangles. Each vertex in these
   * rectangles has u and v coordinates, corresponding to its location
   * in the unclipped tile, and a tile coordinate from the tile's
   * contents in nametable space. So each vertex has a pixel-space
   * coordinate and a pattern-table-space coordinate.
   *
   * 3. The vertex shader sees the pixel-space coordinates of the
   * polygons comprising the tiles, and maps them to GL space.
   *
   * 4. The fragment shader sees the pattern-table-space coordinates
   * and maps them to actual colors (with the help of palettes).
   *
   */

  // For this function, I'll be using hungarian notation with prefix
  // ss to represent screen-space coords, ps to represent pixel-space
  // coords, and nts to represent nametable-space coords.

  // TODO: actually do something with the z coord here. We need to
  // increase it as we change scroll regions, pass it into the shader,
  // and make the necessary changes for the shader to use it.
  float priority = 0.0;

  // Clear our vertex collection, but request that its memory not be
  // deallocated. In practice, it looks like memory won't be
  // deallocated under most compilers anyway, but (according to
  // cplusplus.com) the spec doesn't guarantee either way.
  bgVertices.reserve(bgVertices.size());
  bgVertices.clear();

  // The first element of the scroll changes vector needs to contain
  // the initial scroll state of the frame. Assert that there is a
  // first element and that it does in fact start at the beginning of
  // the screen.
  assert(scrollChanges.size() > 0);
  assert(scrollChanges.at(0).ps_x_start == 0);
  assert(scrollChanges.at(0).ps_y_top == 0);

  for (vector<scrollChange>::iterator it = scrollChanges.begin();
       it < scrollChanges.end();
       it++) {

    // pixel-space boundary coordinates of scroll region
    pixel_coord psRegionXStart = it->ps_x_start;
    pixel_coord psRegionYTop = it->ps_y_top;
    pixel_coord psRegionXEnd, psRegionYBottom;
    if (it+1 == scrollChanges.end()) {
      psRegionYBottom = VISIBLE_SCANLINES - 1;
      psRegionXEnd = VISIBLE_COLUMNS;
    } else {
      // While we're here, check to make sure the scroll regions are
      // strictly increasing over pixel space, lexicographically
      assert(((it+1)->ps_y_top > it->ps_y_top)
             ||
             (((it+1)->ps_y_top == it->ps_y_top)
              &&
              ((it+1)->ps_x_start > it->ps_x_start)));
    }
    // We'd also better still be on the screen. This puts bounds on
    // the start coordinates; between that and asserting that start
    // coordinates are strictly increasing (lexicographically), we
    // have a bound on how long this loop is allowed to continue, so
    // we'll catch errors that'd make it go very long.
    assert(psRegionXStart < VISIBLE_COLUMNS);
    assert(psRegionYTop < VISIBLE_SCANLINES);

    // scroll-space offset coordinates of scroll region
    scroll_coord ssScrollX = it->ss_x_offset;
    scroll_coord ssScrollY = it->ss_y_offset;
    scroll_coord ssFineScrollX = ssScrollX % 8;
    scroll_coord ssFineScrollY = ssScrollY % 8;


    // Iterate through every tile represented in our scroll region.
    // psTileTop and psTileLeft represent the top-left coordinates of
    // the tile /before/ clipping.

    // Start at the pixel-space boundaries of the scroll region and
    // subtract the fine scroll. This will put us at the boundary of
    // the first tile to appear on the screen.
    for (pixel_coord psTileTop =
           psRegionYTop - (pixel_coord) ssFineScrollY;
         psTileTop < psRegionYBottom;
         psTileTop += 8) {

      scroll_coord ssTileTop =
        (psTileTop + ssScrollY) % scrollHeight();
      assert(0 <= ssTileTop < scrollHeight());
      assert(ssTileTop % 8 == 0);
      ntab_coord ntsTileY = (ntab_coord) (ssTileTop / 8);


      // The x-coordinate starts similarly to the y-coordinate, except
      // that it always starts at the left of the screen (and goes to
      // the right).
      for (pixel_coord psTileLeft =
             - (pixel_coord) ssFineScrollX;
           psTileLeft < VISIBLE_COLUMNS;
           psTileLeft += 8) {

        int ssTileLeft =
          (psTileLeft + ssScrollX) % scrollWidth();
        assert(0 <= ssTileLeft < scrollWidth());
        assert(ssTileLeft % 8 == 0);
        ntab_coord ntsTileX = (ntab_coord) (ssTileLeft / 8);



        /* TODO: clip the top and left of the tile, according to the
         * following rules:
         *
         * - If we're above the top of the scroll region, and entirely
         *   to the left (i.e. our pixel-space x is >= the start
         *   coord's x), then clip y to the start coord's y, and clip
         *   v accordingly.
         *
         * - If we're above /or at/ the top, and entirely to the right
         *   (our rightmost pixel space x is < the start coord's x),
         *   then clip y to the start coord's y plus 1, and clip v
         *   accordingly.
         *
         * - If we're above or at the top, and our x boundaries
         *   straddle the start, then we actually need to spilt this
         *   into two rectangles.
         *
         */


        pixel_coord psRectLeft = psTileLeft;
        pixel_coord psRectRight = psTileLeft + 8;
        pixel_coord psRectTop = psTileTop;
        pixel_coord psRectBottom = psTileTop + 8;

        // bottom-right of uv coordinates is always 1,1. Top-right is
        // clipped if rectangle is clipped.
        ptab_tile_coord tile = tileIndices[ntsTileX][ntsTileY];
        ptab_uv_coord u_left = 0.0 + (psRectLeft - psTileLeft) / 8.0;
        ptab_uv_coord u_right = 1.0;
        ptab_uv_coord v_top = 0.0 + (psRectTop - psTileTop) / 8.0;
        ptab_uv_coord v_bottom = 1.0;

        int palette_index = paletteIndices[ntsTileX][ntsTileY];


        appendRect(
          bgVertices,
          psRectLeft, psRectRight, psRectTop, psRectBottom,
          priority, // TODO we don't do anything with priority so far
          tile, u_left, u_right, v_top, v_bottom,
          palette_index);
      } // loop over x coordinates
    } // loop over y coordinates
  } // loop over scrollChanges

  // We've set up the bgVertices vector, so now send over all those
  // vertices to opengl.

  drawVertices(bgVertices,
               bgVbo, bgPtabName, BG_PATTERN_TABLE_TEXTURE,
               BG_PATTERN_TABLE_TEXID, bgPalettes);

}

void Screen::drawSprites() {
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
    oamEntry sprite = oam[oam_i];
    if (sprite.y_minus_one >= 0xef) {
      // The sprite is wholly off the screen; ignore it
      continue;
    }
    // preceding check ensures this won't overflow
    unsigned char spritetop = sprite.y_minus_one + 1;

    pixel_coord x_left = sprite.x;
    pixel_coord x_right = sprite.x + 8;

    pixel_coord y_top = sprite.y_minus_one + 1;
    pixel_coord y_bottom = y_top + 8;

    ptab_uv_coord u_left =
      (sprite.attributes & OAM_FLIP_HORIZONTAL ? 1 : 0);
    ptab_uv_coord u_right = 1 - u_left;

    ptab_uv_coord v_top =
      (sprite.attributes & OAM_FLIP_VERTICAL ? 1 : 0);
    ptab_uv_coord v_bottom = 1 - v_top;

    ptab_tile_coord tile = sprite.tile;
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
        } else {
          if (x_left <= DONKEY_KONG_BIG_HEAD_INCREASE) {
            x_left = 0;
          } else {
            x_left -= DONKEY_KONG_BIG_HEAD_INCREASE;
          }
        }
      }
    }

    appendRect(
      spriteVertices,
      x_left, x_right,
      y_top, y_bottom,
      0.1, // TODO priority
      tile,
      u_left, u_right,
      v_top, v_bottom,
      palette_index);

  }

  drawVertices(spriteVertices,
               spriteVbo, spritePtabName,
               SPRITE_PATTERN_TABLE_TEXTURE,
               SPRITE_PATTERN_TABLE_TEXID,
               spritePalettes);
}

void Screen::appendRect(
    vector<glVertex> &vertices,
    pixel_coord x_left, pixel_coord x_right,
    pixel_coord y_top, pixel_coord y_bottom,
    float priority,
    ptab_tile_coord tile,
    ptab_uv_coord u_left, ptab_uv_coord u_right,
    ptab_uv_coord v_top, ptab_uv_coord v_bottom,
    unsigned char palette_index
    ) {
  glVertex bottomLeft =
    {x_left, y_bottom, priority,
     tile, u_left, v_bottom, palette_index};
  glVertex bottomRight =
    {x_right, y_bottom, priority,
     tile, u_right, v_bottom, palette_index};
  glVertex topLeft =
    {x_left, y_top, priority,
     tile, u_left, v_top, palette_index};
  glVertex topRight =
    {x_right, y_top, priority,
     tile, u_right, v_top, palette_index};

  // first triangle
  vertices.push_back(bottomLeft);
  vertices.push_back(bottomRight);
  vertices.push_back(topRight);
  // second triangle
  vertices.push_back(bottomLeft);
  vertices.push_back(topRight);
  vertices.push_back(topLeft);
}

// Polls for keys, returns their state in a one-byte bitfield (masks
// defined in header)
unsigned char Screen::pollKeys() {
  // Currently, we're polling events here and in draw(). Is that a
  // problem? Not sure.
  glfwPollEvents();

  if(glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS) {
    exit(0);
  }

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

// ctypes interface

extern "C" {

  Screen *ex_constructScreen(int st) {
    return new Screen((ScrollType) st);
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

  void ex_setTileIndices(Screen *sc, unsigned char *indices,
                         unsigned int len) {
    sc->setTileIndices(indices, len);
  }

  void ex_setPaletteIndices(Screen *sc, unsigned char *indices,
                            unsigned int len) {
    sc->setPaletteIndices(indices, len);
  }

  void ex_setOam(Screen *sc, unsigned char *oamBytes) {
    sc->setOam(oamBytes);
  }

  void ex_setMask(Screen *sc, unsigned char m) {
    sc->setMask(m);
  }

  void ex_setScrollCoords(Screen *sc, unsigned int x, unsigned int y) {
    sc->setScrollCoords(x,y);
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
