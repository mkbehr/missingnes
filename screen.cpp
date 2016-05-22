// #include <GLFW/glfw3.h>

#include <iostream>
#include <string>
#include <sstream>
#include <fstream>

#ifdef __APPLE__
#include <OpenGL/gl.h>
#include <OpenGL/glu.h>
#include <GLUT/glut.h>
#else
#include <GL/glut.h>
#endif

using namespace std;

#include "screen.h"

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
  case GL_STACK_OVERFLOW:
    return "Stack overflow";
  case GL_STACK_UNDERFLOW:
    return "Stack underflow";
  case GL_OUT_OF_MEMORY:
    return "Out of memory";
  case GL_INVALID_FRAMEBUFFER_OPERATION:
    return "Invalid framebuffer operation";
  // case GL_CONTEXT_LOST:
  //   return "Context lost";
  case GL_TABLE_TOO_LARGE:
    return "Table too large";
  default:
    return "Unrecognized error";
  }
}

void checkGlErrors(int continue_after_err) {
  GLenum err = GL_NO_ERROR;
  while ((err = glGetError())) {
    const char *errMsg = glErrorString(err);
    cerr << "GL error: " << errMsg
	 << " (" << hex << err << ")\n";
    if (!continue_after_err) {
      die();
    }
  }
}

Screen::Screen(void) {

  // TODO assign pointer to PPU object

  if (initWindow(&window) < 0) {
    cerr << "Couldn't create window\n";
    exit(-1);
  }
  if (glfwGetWindowAttrib(window, GLFW_CONTEXT_VERSION_MAJOR) < 3) {
    cerr << "Screen: Error: GL major version too low\n";
    die();
  }

  glfwSetInputMode(window, GLFW_STICKY_KEYS, 1);

  // // bind a vertex array
  // GLuint va;
  // // TODO rewrite this so it'll compile on not just os x
  // glGenVertexArraysAPPLE(1, &va);
  // glBindVertexArrayAPPLE(va);
  // checkGlErrors(0);

  initShaders();


  glGenBuffers(1, &bgVbo);
  glGenBuffers(1, &spriteVbo);
  glGenTextures(1, &bgPtabName);
  glGenTextures(1, &spritePtabName);

  checkGlErrors(0);

  lastBgPalette = -1;
  lastSpritePalette = -1;
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
  stringstream vertBuffer;
  vertBuffer << vertFile.rdbuf();
  // This approach makes the string turn into the empty string for some reason
  // const char *vertSrc = vertBuffer.str().c_str();
  string vertStr = vertBuffer.str();
  const char *vertSrc = vertStr.c_str();
  int vertSrcLen = vertStr.length();
  ifstream fragFile(FRAGMENT_SHADER_FILE);
  stringstream fragBuffer;
  fragBuffer << fragFile.rdbuf();
  string fragStr = fragBuffer.str();
  const char *fragSrc = fragStr.c_str();
  int fragSrcLen = fragStr.length();


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
  GLuint shader = glCreateProgram();
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

int main(void) {
  Screen foo = Screen();
  glfwTerminate();
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
  window = glfwCreateWindow(640, 480,
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

  // This is the render loop. Don't actually do it here.

  // /* Loop until the user closes the window */
  // while (!glfwWindowShouldClose(window))
  // {
  //     /* Render here */
  //   glClearColor(0.4, 0.4, 1.0, 1.0);
  //   glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_ACCUM_BUFFER_BIT);

  //     /* Swap front and back buffers */
  //     glfwSwapBuffers(window);

  //     /* Poll for and process events */
  //     glfwPollEvents();
  // }

  // glfwTerminate();

  *window_p = window;
  return 0;
}
