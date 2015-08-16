"""Handle drawing objects to the screen. The code is seperate from
ppu.py because this doesn't handle the PPU's internal state - the view
to ppu.py's controller, let's say. (or is that the model? should we
have more separation?)

"""
import ctypes

import pyglet
from pyglet.window import key
#from pyglet.gl import *
import pyglet.gl

from OpenGL.GL import *
from OpenGL.arrays import vbo
from OpenGL.GL import shaders
from OpenGL.GL.ARB import vertex_array_object # I don't know
from OpenGL.GLU import *

import glfw

from PIL import Image
import numpy as np

import palette
import ppu

# For now, we're going to keep pyglet's redraw interval decoupled from
# the ppu's frame interval. That's not ideal, but I'll see if it needs
# fixing once it's done.

# Actually hahaha that's a lie we're going to totally couple them by
# writing our own pyglet event loop. Pyglet strongly disrecommends
# this but whatever, we can decouple them later.

# Note: pyglet will eventually handle keyboard input and sound. That
# might take place in a different file.

TILE_ROWS = ppu.VISIBLE_SCANLINES/8
TILE_COLUMNS = ppu.VISIBLE_COLUMNS/8

SCREEN_WIDTH = ppu.VISIBLE_COLUMNS
SCREEN_HEIGHT = ppu.VISIBLE_SCANLINES

class Screen(object):

    def __init__(self, _ppu): # underscore to patch over sloppy naming hiding the ppu module

        self.ppu = _ppu

        # config = pyglet.gl.Config(major_version=3, minor_version=0)

        # self.window = pyglet.window.Window(config = config, width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
        # self.window.on_draw = self.on_draw

        # self.keys = key.KeyStateHandler()
        # self.window.push_handlers(self.keys)

        # dummyImage = pyglet.image.ImageData(1, 1, 'RGBA', "\x00\x00\x00\x00", pitch= 4)

        # # playing around with possible ways of drawing things quickly
        # self.bgBatch = pyglet.graphics.Batch()
        # self.bgSprites = [
        #     [pyglet.sprite.Sprite(dummyImage, x*8, SCREEN_HEIGHT - y*8 - 8, batch=self.bgBatch)
        #      for y in range(TILE_ROWS)]
        #     for x in range(TILE_COLUMNS)]
        # self.bgTiles = [
        #     [dummyImage for y in range(TILE_ROWS)]
        #     for x in range(TILE_COLUMNS)]
        # self.bgTextureNames = [
        #     # I don't really know what I'm doing here
        #     [GLuint(0) for y in range(TILE_ROWS)]
        #     for x in range(TILE_COLUMNS)]
        # for x in xrange(TILE_COLUMNS):
        #     for y in xrange(TILE_ROWS):
        #         glGenTextures(1, ctypes.byref(self.bgTextureNames[x][y]))
        #         glBindTexture(GL_TEXTURE_2D, self.bgTextureNames[x][y].value)
        #         glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 1, 1, 0, GL_RGBA, GL_UNSIGNED_BYTE, "\x00\x00\x00\x00")
        # self.bgVbos = [
        #     [GLuint(0) for y in range(TILE_ROWS)]
        #     for x in range(TILE_COLUMNS)]
        # for x in xrange(TILE_COLUMNS):
        #     for y in xrange(TILE_ROWS):
        #         glGenBuffers(1, ctypes.byref(self.bgVbos[x][y]))
        #         glBindBuffer(GL_ARRAY_BUFFER, self.bgVbos[x][y].value)
        #         left = x * 8.0 / SCREEN_WIDTH
        #         right = (x * 8.0 + 1.0) / SCREEN_WIDTH
        #         # are top and bottom right here? WHO KNOWS
        #         bottom = (SCREEN_HEIGHT - y*8.0 - 8.0) / SCREEN_WIDTH
        #         top = (SCREEN_HEIGHT - y*8.0) / SCREEN_WIDTH
        #         vertexList = [
        #             left, bottom, 0.0, 0.0,
        #             right, bottom, 1.0, 0.0,
        #             right, top, 1.0, 1.0,
        #             left, top, 0.0, 1.0
        #             ]
        #         vertexFloats = (ctypes.c_float * len(vertexList)) (*vertexList)
        #         glBufferData(GL_ARRAY_BUFFER, len(vertexList), vertexFloats, GL_STATIC_DRAW)

        # self.spriteBatch = pyglet.graphics.Batch()
        # self.spriteSprites = [pyglet.sprite.Sprite(dummyImage, 0, 0, batch=self.spriteBatch)
        #                       for sprite_i in range(ppu.OAM_SIZE / ppu.OAM_ENTRY_SIZE)]

        # TODO glfw stuff?

        if not glfw.init():
            assert(false) # fuck it

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3);
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 2);
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE);
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE);

        window = glfw.create_window(SCREEN_WIDTH, SCREEN_HEIGHT, "Hello World", None, None)
        self.window = window

        if not window:
            glfw.terminate()

        assert (glfw.get_window_attrib(window, glfw.CONTEXT_VERSION_MAJOR) >= 3)

        vao_id = GLuint(0)
        # I hate python gl bindings
        pyglet.gl.glGenVertexArrays(1, ctypes.byref(vao_id))
        pyglet.gl.glBindVertexArray(vao_id.value)

        vertexShaderSrc = """#version 330

        in vec2 position;
        in vec2 texcoord;

        out vec2 Texcoord;

        void main()
        {
          gl_Position = vec4(position, 0.0, 1.0);
          Texcoord = texcoord;
        }"""
        vertexShader = shaders.compileShader(vertexShaderSrc, GL_VERTEX_SHADER)

        fragmentShaderSrc = """#version 330

        in vec2 Texcoord;

        out vec4 outColor;

        uniform sampler2D tex;

        void main()
        {
          outColor = texture(tex, Texcoord);
        }"""
        fragmentShader = shaders.compileShader(fragmentShaderSrc, GL_FRAGMENT_SHADER)
        self.shader = shaders.compileProgram(vertexShader, fragmentShader)
        glUseProgram(self.shader)

        self.positionAttrib = glGetAttribLocation(self.shader, "position")
        self.texcoordAttrib = glGetAttribLocation(self.shader, "texcoord")

        self.bgTextureNames = [
            # I don't really know what I'm doing here
            [GLuint(0) for y in range(TILE_ROWS)]
            for x in range(TILE_COLUMNS)]
        for x in xrange(TILE_COLUMNS):
            for y in xrange(TILE_ROWS):
                glGenTextures(1, ctypes.byref(self.bgTextureNames[x][y]))
                glBindTexture(GL_TEXTURE_2D, self.bgTextureNames[x][y].value)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 1, 1, 0, GL_RGBA, GL_UNSIGNED_BYTE, "\x00\x00\x00\x00")
        self.bgVbos = [
            [GLuint(0) for y in range(TILE_ROWS)]
            for x in range(TILE_COLUMNS)]
        for x in xrange(TILE_COLUMNS):
            for y in xrange(TILE_ROWS):
                glGenBuffers(1, ctypes.byref(self.bgVbos[x][y]))
                glBindBuffer(GL_ARRAY_BUFFER, self.bgVbos[x][y].value)
                left = x * 8.0 / SCREEN_WIDTH
                right = ((x+1) * 8.0) / SCREEN_WIDTH
                # are top and bottom right here? WHO KNOWS
                bottom = (SCREEN_HEIGHT - y*8.0 - 8.0) / SCREEN_WIDTH
                top = (SCREEN_HEIGHT - y*8.0) / SCREEN_WIDTH
                print (bottom, top) # bottom should be less than top, I think
                # map to coordinates with boundaries of -1 and 1
                left = left * 2.0 - 1
                right = right * 2.0 - 1
                bottom = bottom * 2.0 - 1
                top = top * 2.0 - 1
                # triangles need to be counterclockwise to be front-facing
                vertexList = [
                    left, bottom, 0.0, 0.0,
                    right, bottom, 1.0, 0.0,
                    right, top, 1.0, 1.0,
                    left, top, 0.0, 1.0,
                    ]
                vertexFloats = (ctypes.c_float * len(vertexList)) (*vertexList)
                glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(vertexFloats), vertexFloats, GL_STATIC_DRAW)

    def tick(self, frame): # TODO consider turning this into a more general callback that the ppu gets
        self.on_draw()

        return
        pyglet.clock.tick()

        for window in pyglet.app.windows:
            window.switch_to()
            window.dispatch_events()
            window.dispatch_event('on_draw')
            window.flip()

        # Handle controller input.

        # TODO: use fewer magic numbers and put together a proper
        # structure for this code.

        # forgive me demeter for I have sinned
        ips = self.ppu.cpu.controller.inputState.states

        # TODO: instead of just tracking keys, consider making sure
        # that when the user presses a button, that button is pressed
        # in the next frame, even if it's released before the frame is
        # processed.
        ips[0] = self.keys[key.A] # A
        ips[1] = self.keys[key.S] # B
        ips[2] = self.keys[key.BACKSLASH] # select: mapping to \ for now
        ips[3] = (self.keys[key.ENTER] or self.keys[key.RETURN]) # start
        ips[4] = self.keys[key.UP]
        ips[5] = self.keys[key.DOWN]
        ips[6] = self.keys[key.LEFT]
        ips[7] = self.keys[key.RIGHT]

    def on_draw(self):
        #glViewport(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        
        (bg_r, bg_g, bg_b) = palette.PALETTE[self.ppu.universalBg]
        (bg_r, bg_g, bg_b) = (128,128,128) # DEBUG
        glClearColor(bg_r / 255.0, bg_g / 255.0, bg_b / 255.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_ACCUM_BUFFER_BIT)
        # self.bgBatch.draw()
        # for x in xrange(TILE_COLUMNS):
        #     for y in xrange(TILE_ROWS):
        #         self.bgTiles[x][y].blit(x*8, SCREEN_HEIGHT - y*8 - 8)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

        

        for x in xrange(TILE_COLUMNS):
            for y in xrange(TILE_ROWS):
                glBindTexture(GL_TEXTURE_2D, self.bgTextureNames[x][y].value)
                glBindBuffer(GL_ARRAY_BUFFER, self.bgVbos[x][y].value)

                stride = 4 * ctypes.sizeof(ctypes.c_float)

                glVertexAttribPointer(self.positionAttrib, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
                glEnableVertexAttribArray(self.positionAttrib)
                glVertexAttribPointer(self.texcoordAttrib, 2, GL_FLOAT, GL_FALSE, stride,
                                      ctypes.c_void_p(2 * ctypes.sizeof(ctypes.c_float)))
                glEnableVertexAttribArray(self.texcoordAttrib)
                glUniform1i(glGetUniformLocation(self.shader, "tex"), 0)
                glDrawArrays(GL_TRIANGLE_FAN, 0, 4)
        #self.spriteBatch.draw()

        # DEBUG
        # glBindTexture(GL_TEXTURE_2D, self.bgTextureNames[4][4].value)
        # glActiveTexture(GL_TEXTURE0)
        # glBindBuffer(GL_ARRAY_BUFFER, self.bgVbos[4][4].value)
        # # triangles need to be counterclockwise to be front-facing
        # right = 0.9
        # left = -0.9
        # bottom = -0.9
        # top = 0.9
        # vertexList = [
        #     left, bottom, 0.0, 0.0,
        #     right, bottom, 1.0, 0.0,
        #     right, top, 1.0, 1.0,
        #     left, top, 0.0, 1.0,
        # ]
        # vertexFloats = (ctypes.c_float * len(vertexList)) (*vertexList)
        # glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(vertexFloats), vertexFloats, GL_STATIC_DRAW)

        # stride = 4 * ctypes.sizeof(ctypes.c_float)
        
        # glVertexAttribPointer(self.positionAttrib, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        # glEnableVertexAttribArray(self.positionAttrib)
        # glVertexAttribPointer(self.texcoordAttrib, 2, GL_FLOAT, GL_FALSE, stride,
        #                       ctypes.c_void_p(2 * ctypes.sizeof(ctypes.c_float)))
        # glEnableVertexAttribArray(self.texcoordAttrib)
        # glUniform1i(glGetUniformLocation(self.shader, "tex"), 0)
        # glDrawArrays(GL_TRIANGLE_FAN, 0, 4)
        # END DEBUG
        

        glfw.swap_buffers(self.window)
