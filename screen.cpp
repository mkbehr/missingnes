#include <cstddef>
#include <iostream>
#include <string>
#include <sstream>
#include <fstream>

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

  // There is a more c++ style way to get the array length here. Eh.
  cerr << "Initializing local palettes\n";
  memset(localPalettes, 0, LOCAL_PALETTES_LENGTH * sizeof(float));
  // DEBUG
  for (int i=0; i < LOCAL_PALETTES_LENGTH; i++) {
    localPalettes[i] = (float) (i%10);
  }

  // TODO also initialize sprite ptab
  float zeroPtab[PATTERN_TABLE_LENGTH] = {};
  // DEBUG
  for (int i=0; i < PATTERN_TABLE_LENGTH; i++) {
    zeroPtab[i] = (float) (i%4);
  }
  cerr << "Initializing background pattern table texture\n";
  setBgPatternTable(zeroPtab);
  cerr << "Initializing sprite pattern table texture\n";
  setSpritePatternTable(zeroPtab);

  // TODO set up tileIndices, paletteIndices, bgVertices

  initBgVertices();
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
  printf("Read vertex shader file with length %d\n", vertSrcLen);
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
  printf("Read fragment shader file with length %d\n", vertSrcLen);


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
  } else {
    // DEBUG
    cerr << "Vertex shader compiled\n";
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
  } else {
    // DEBUG
    cerr << "Fragment shader compiled\n";
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
  } else {
    // DEBUG
    cerr << "Shader program linked\n";
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

      struct bgVertex bottomLeft =
	{x_left, y_bottom, x_left_high,
	 tile, u_left, v_bottom, palette_index};
      struct bgVertex bottomRight =
	{x_right, y_bottom, x_right_high,
	 tile, u_right, v_bottom, palette_index};
      struct bgVertex topLeft =
	{x_left, y_top, x_left_high,
	 tile, u_left, v_top, palette_index};
      struct bgVertex topRight =
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

// Input should be a pointer to LOCAL_PALETTES_LENGTH floats
void Screen::setLocalPalettes(float *localPaletteInput) {
      memcpy(localPalettes, localPaletteInput,
	     LOCAL_PALETTES_LENGTH * sizeof(float));
}

void Screen::setBgPatternTable(float *bgPtabInput) {
  /* Note: according to stackoverflow, glTexImage2D allows the memory
     to be freed after the call, so I don't have to worry about
     copying the input over to somewhere stable. I can't find the part
     of the API that actually says that, but for now I'll trust it.

     http://stackoverflow.com/questions/26499361/opengl-what-does-glteximage2d-do
  */

  glBindTexture(GL_TEXTURE_2D, bgPtabName);
  glActiveTexture(BG_PATTERN_TABLE_TEXTURE);
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, 8*PATTERN_TABLE_TILES, 8,
	       0, GL_RED, GL_FLOAT, bgPtabInput);
  checkGlErrors(0);
}

void Screen::setSpritePatternTable(float *spritePtabInput) {
  glBindTexture(GL_TEXTURE_2D, spritePtabName);
  glActiveTexture(SPRITE_PATTERN_TABLE_TEXTURE);
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, 8*PATTERN_TABLE_TILES, 8,
	       0, GL_RED, GL_FLOAT, spritePtabInput);
  checkGlErrors(0);
}


void Screen::drawToBuffer() {
  // State we need by the time we finish this (for background):
  // - universalBg needs to be set to the universal background palette index
  // - localPalettes needs to be set to a buffer with the local palettes
  // - BG_PATTERN_TABLE_TEXTURE needs to be populated with the background pattern table
  // - we need data for the actual tiles (tileIndices and paletteIndices from the python, set by the ppu)
  //   (so maybe keep the ppu setting that, and then move it from python to c++)

  unsigned char universalBg = 0x2c; // TODO
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
    // TODO maintain bg palette table (or, uh, make sure it's maintained)

    // do we need to call these again? unclear. python code did it but
    // I don't know why.
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

    checkGlErrors(0);

    // Set tile and palette. The rest of the values in the VBO won't change.
    for (int x = 0; x < TILE_COLUMNS; x++) {
      for (int y = 0; y < TILE_ROWS; y++) {
	// TODO get tile and palette
	unsigned char tile = 0;
	unsigned char palette = 0;
	int screen_tile_index = (x + y*TILE_COLUMNS) * VERTICES_PER_TILE;
	for (int vertex_i = 0; vertex_i < VERTICES_PER_TILE; vertex_i++) {
	  bgVertices[screen_tile_index + vertex_i].tile = tile;
	  bgVertices[screen_tile_index + vertex_i].palette = palette;
	}
      }
    }

    int stride = sizeof(struct bgVertex);
    glBufferData(GL_ARRAY_BUFFER, sizeof(bgVertices),
		 bgVertices, GL_DYNAMIC_DRAW);
    checkGlErrors(0);
    glVertexAttribPointer(xyAttrib, 2, GL_UNSIGNED_BYTE, GL_FALSE, stride,
			  (const GLvoid *) offsetof(struct bgVertex, x_low));
    glEnableVertexAttribArray(xyAttrib);
    checkGlErrors(0);
    glVertexAttribPointer(xHighAttrib, 1, GL_UNSIGNED_BYTE, GL_FALSE, stride,
			  (const GLvoid *) offsetof(struct bgVertex, x_high));
    glEnableVertexAttribArray(xHighAttrib);
    checkGlErrors(0);
    glVertexAttribPointer(tuvAttrib, 3, GL_UNSIGNED_BYTE, GL_FALSE, stride,
			  (const GLvoid *) offsetof(struct bgVertex, tile));
    glEnableVertexAttribArray(tuvAttrib);
    checkGlErrors(0);
    glVertexAttribPointer(paletteNAttrib, 1, GL_UNSIGNED_BYTE, GL_FALSE, stride,
			  (const GLvoid *) offsetof(struct bgVertex, palette));
    glEnableVertexAttribArray(paletteNAttrib);
    checkGlErrors(0);

    glUniform1i(glGetUniformLocation(shader, "patternTable"),
		BG_PATTERN_TABLE_TEXID);
    checkGlErrors(0);

    // FIXME magic number 16
    glUniform4fv(glGetUniformLocation(shader, "localPalettes"), 16,
		 localPalettes);
    checkGlErrors(0);

    glDrawArrays(GL_TRIANGLES, 0, N_BG_VERTICES);
    checkGlErrors(0);
  }
  if (DRAW_SPRITES) {
    ; // TODO
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

// int main(void) {
//   Screen foo = Screen();
//   cerr << "Beginning render loop\n";
//   foo.testRenderLoop();
//   glfwTerminate();
//   return 0;
// }

using namespace boost::python;

BOOST_PYTHON_MODULE(boostscreen) {
  class_<Screen>("Screen")
    .def("drawToBuffer", &Screen::drawToBuffer)
    .def("draw", &Screen::draw)
    ;
}
