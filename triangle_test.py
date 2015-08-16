import glfw
from OpenGL.GL import *
import pyglet.gl
from OpenGL.GL import shaders
from OpenGL.arrays import vbo

from OpenGLContext.arrays import *

import numpy as np

import ctypes

glfw.init()
glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3);
glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 2);
glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE);
glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE);

window = glfw.create_window(256, 240, "Hello World", None, None)

assert (glfw.get_window_attrib(window, glfw.CONTEXT_VERSION_MAJOR) >= 3)

print (glfw.get_window_attrib(window, glfw.CONTEXT_VERSION_MAJOR),
       glfw.get_window_attrib(window, glfw.CONTEXT_VERSION_MINOR))

vao_id = GLuint(0)
# I hate python gl bindings
pyglet.gl.glGenVertexArrays(1, ctypes.byref(vao_id))
pyglet.gl.glBindVertexArray(vao_id.value)

vertexShaderSrc = """#version 150

in vec2 position;
in vec3 color;

out vec3 fColor;

void main()
{
gl_Position = vec4(position, 0.0, 1.0);
fColor = color;
}"""
vertexShader = shaders.compileShader(vertexShaderSrc, GL_VERTEX_SHADER)

fragmentShaderSrc = """#version 150

in vec3 fColor;

out vec4 outColor;

void main()
{
outColor = vec4(fColor, 1.0);
}"""
fragmentShader = shaders.compileShader(fragmentShaderSrc, GL_FRAGMENT_SHADER)
program = shaders.compileProgram(vertexShader, fragmentShader)
shaders.glUseProgram(program)

# fooVbo = vbo.VBO(
#     array([
#         [0.0,0.5],
#         [0.5,-0.5],
#         [-0.5,-0.5]
#         ],'f'))

# fooVbo.bind()

vertices = [
    0.0,  0.5, 1., 0., 0., # Vertex 1 (X, Y, R, G, B)
    0.5, -0.5, 0., 1., 0., # Vertex 2 (X, Y, R, G, B)
    -0.5, -0.5, 0., 0., 1. # Vertex 3 (X, Y, R, G, B)
  ];
cVertices = (ctypes.c_float * len(vertices)) (*vertices)

# Request a buffer slot from GPU
buffer = glGenBuffers(1)

# Make this buffer the default one
glBindBuffer(GL_ARRAY_BUFFER, buffer)

# Upload data
glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(cVertices), cVertices, GL_STATIC_DRAW)

stride = 5 * ctypes.sizeof(ctypes.c_float)

offset = ctypes.c_void_p(0)
posAttrib = glGetAttribLocation(program, "position")
glVertexAttribPointer(posAttrib, 2, GL_FLOAT, GL_FALSE, stride, offset)
glEnableVertexAttribArray(posAttrib)

offset = ctypes.c_void_p(2 * ctypes.sizeof(ctypes.c_float))
colorAttrib = glGetAttribLocation(program, "color")
glVertexAttribPointer(colorAttrib, 3, GL_FLOAT, GL_FALSE, stride, offset)
glEnableVertexAttribArray(colorAttrib)


while True:
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glClear(GL_COLOR_BUFFER_BIT)


    glDrawArrays(GL_TRIANGLES, 0, 3)
    glfw.swap_buffers(window)
    import time
    time.sleep(1.0/60)
