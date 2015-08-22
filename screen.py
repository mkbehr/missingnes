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

N_VERTICES = TILE_ROWS * TILE_COLUMNS * 4

PATTERN_TABLE_TILES = 256

BG_PATTERN_TABLE_TEXTURE = GL_TEXTURE0
BG_PATTERN_TABLE_TEXID = 0
# TODO other texture ids go here


class Screen(object):

    def __init__(self, _ppu): # underscore to patch over sloppy naming hiding the ppu module

        self.ppu = _ppu


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
        # use pyglet because pyopengl doesn't like these functions
        pyglet.gl.glGenVertexArrays(1, ctypes.byref(vao_id))
        pyglet.gl.glBindVertexArray(vao_id.value)

        vertexShaderSrc = """#version 330

        in uvec2 xy;
        in uvec3 v_tuv;
        in uint v_palette_n;

        out vec3 f_uvt;
        //out uint f_palette_n;

        void main()
        {
          gl_Position = vec4(xy.x / 256.0, xy.y / 240.0, 0.0, 1.0);
          f_uvt = vec3(v_tuv.y/8.0, v_tuv.z/8.0, v_tuv.x);
          //f_palette_n = v_palette_n;
        }"""
        vertexShader = shaders.compileShader(vertexShaderSrc, GL_VERTEX_SHADER)

        fragmentShaderSrc = """#version 330

        in vec3 f_uvt;
        //in int f_palette_n;

        out vec4 outColor;

        uniform usampler2DArray patternTable;
        uniform uint[16] localPalettes;
        uniform sampler1D globalPalette;

        void main()
        {
          uint localPaletteIndex;
          localPaletteIndex = texture(patternTable, f_uvt).r;
          // TODO: we can probably select the local palette in the vertex shader
        /*
          globalPaletteIndex = localPalettes[f_palette_n * 4 + localPaletteIndex];
          outColor = texture(globalPalette, globalPaletteIndex);
        */
        // DEBUG:
          float greyShade = localPaletteIndex / 4.0;
          outColor = vec4(greyShade, greyShade, greyShade, 1.0);
        }"""
        fragmentShader = shaders.compileShader(fragmentShaderSrc, GL_FRAGMENT_SHADER)
        self.shader = shaders.compileProgram(vertexShader, fragmentShader)
        glUseProgram(self.shader)

        self.xyAttrib = glGetAttribLocation(self.shader, "xy")
        self.tuvAttrib = glGetAttribLocation(self.shader, "v_tuv")
        self.paletteNAttrib = glGetAttribLocation(self.shader, "v_palette_n")

        self.lastBgPalette = None

        self.bgVbo = glGenBuffers(1)
        
        self.bgPtabName = glGenTextures(1)

        # TODO bind global palette 

        # self.bgTextureNames = [
        #     # I don't really know what I'm doing here
        #     [0 for y in range(TILE_ROWS)]
        #     for x in range(TILE_COLUMNS)]
        # for x in xrange(TILE_COLUMNS):
        #     for y in xrange(TILE_ROWS):
        #         self.bgTextureNames[x][y] = glGenTextures(1)
        #         glBindTexture(GL_TEXTURE_2D, self.bgTextureNames[x][y])
        #         glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 1, 1, 0, GL_RGBA, GL_UNSIGNED_BYTE, "\x00\x00\x00\x00")
        # self.bgVbos = [
        #     [0 for y in range(TILE_ROWS)]
        #     for x in range(TILE_COLUMNS)]
        # for x in xrange(TILE_COLUMNS):
        #     for y in xrange(TILE_ROWS):
        #         self.bgVbos[x][y] = glGenBuffers(1)
        #         glBindBuffer(GL_ARRAY_BUFFER, self.bgVbos[x][y])
        #         left = x * 8.0 / SCREEN_WIDTH
        #         right = ((x+1) * 8.0) / SCREEN_WIDTH
        #         # are top and bottom right here? WHO KNOWS
        #         bottom = (SCREEN_HEIGHT - y*8.0 - 8.0) / SCREEN_WIDTH
        #         top = (SCREEN_HEIGHT - y*8.0) / SCREEN_WIDTH
        #         # map to coordinates with boundaries of -1 and 1
        #         left = left * 2.0 - 1
        #         right = right * 2.0 - 1
        #         bottom = bottom * 2.0 - 1
        #         top = top * 2.0 - 1
        #         # triangles need to be counterclockwise to be front-facing
        #         vertexList = [
        #             left, bottom, 0.0, 0.0,
        #             right, bottom, 1.0, 0.0,
        #             right, top, 1.0, 1.0,
        #             left, top, 0.0, 1.0,
        #             ]
        #         vertexFloats = (ctypes.c_float * len(vertexList)) (*vertexList)
        #         glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(vertexFloats), vertexFloats, GL_STATIC_DRAW)

    def tick(self, frame): # TODO consider turning this into a more general callback that the ppu gets
        self.on_draw()

        # # Handle controller input.

        # # TODO: use fewer magic numbers and put together a proper
        # # structure for this code.

        # # forgive me demeter for I have sinned
        # ips = self.ppu.cpu.controller.inputState.states

        # # TODO: instead of just tracking keys, consider making sure
        # # that when the user presses a button, that button is pressed
        # # in the next frame, even if it's released before the frame is
        # # processed.
        # ips[0] = self.keys[key.A] # A
        # ips[1] = self.keys[key.S] # B
        # ips[2] = self.keys[key.BACKSLASH] # select: mapping to \ for now
        # ips[3] = (self.keys[key.ENTER] or self.keys[key.RETURN]) # start
        # ips[4] = self.keys[key.UP]
        # ips[5] = self.keys[key.DOWN]
        # ips[6] = self.keys[key.LEFT]
        # ips[7] = self.keys[key.RIGHT]

    def on_draw(self):
        glBindBuffer(GL_ARRAY_BUFFER, self.bgVbo)

        self.maintainPaletteTable()
        
        (bg_r, bg_g, bg_b) = palette.PALETTE[self.ppu.universalBg]
        (bg_r, bg_g, bg_b) = (128,128,128) # DEBUG
        glClearColor(bg_r / 255.0, bg_g / 255.0, bg_b / 255.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_ACCUM_BUFFER_BIT)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

        # TODO get rid of some of these magic numbers
        vertexList = [0 for x in range(TILE_COLUMNS * TILE_ROWS * 6 * 6)]
        for x in xrange(TILE_COLUMNS):
            for y in xrange(TILE_ROWS):
                x_left = x * 8
                x_right = (x+1) * 8
                y_bottom = (SCREEN_HEIGHT - y*8 - 8)
                y_top = (SCREEN_HEIGHT - y*8)
                tile = 0 # TODO: determined by the nametable
                # TODO see if these uv coordinates are right
                u_left = 0
                u_right = 1
                v_bottom = 0
                v_top = 1
                palette_index = 0 # TODO: determined by the pattern table
                screen_tile_index = (x + y*TILE_ROWS) * 6*6
                vertexList[screen_tile_index : (screen_tile_index+(6*6))] = [
                    # do this as two triangles
                    # first triangle
                    x_left, y_bottom, tile, u_left, v_bottom, palette_index,
                    x_right, y_bottom, tile, u_right, v_bottom, palette_index,
                    x_right, y_top, tile, u_right, v_top, palette_index,
                    # second triangle
                    x_left, y_bottom, tile, u_left, v_bottom, palette_index,
                    x_right, y_top, tile, u_right, v_top, palette_index,
                    x_left, y_top, tile, u_left, v_top, palette_index,
                    ]

        vertices = (ctypes.c_ubyte * (TILE_COLUMNS * TILE_ROWS * 6 * 6)) (*vertexList)

        # FIXME: there may be type problems here, because some
        # of these are floats and some are ints. Probable
        # solution: just make them all (unsigned) ints. Or floats.

        # FIXME magic number
        stride = 6 * ctypes.sizeof(ctypes.c_ubyte)

        glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(vertices), vertices, GL_DYNAMIC_DRAW)

        # TODO point attributes into that big buffer
        xyOffset = ctypes.c_void_p(0)
        glVertexAttribPointer(self.xyAttrib, 2, GL_FLOAT, GL_FALSE, stride, xyOffset)
        glEnableVertexAttribArray(self.xyAttrib)
        tuvOffset = ctypes.c_void_p(2 * ctypes.sizeof(ctypes.c_ubyte))
        glVertexAttribPointer(self.tuvAttrib, 3, GL_FLOAT, GL_FALSE, stride, tuvOffset)
        glEnableVertexAttribArray(self.tuvAttrib)
        # paletteNOffset = ctypes.c_void_p(5 * ctypes.sizeof(ctypes.c_ubyte))
        # glVertexAttribPointer(self.paletteNAttrib, 1, GL_FLOAT, GL_FALSE, stride, paletteNOffset)
        # glEnableVertexAttribArray(self.paletteNAttrib)

        # TODO point uniform arguments

        # this probably involves making sure that our textures
        # are bound to particular GL_TEXTURE{foo} and then
        # passing foo to the TODOs here.

        glUniform1i(glGetUniformLocation(self.shader, "patternTable"), BG_PATTERN_TABLE_TEXID)
        # glUniform1i(glGetUniformLocation(self.shader, "globalPalette"), TODO)

        # and localPalettes.
        # glUniformTODO(glGetUniformLocation(self.shader, "localPalettes"), TODO)

        # Finally, we should be able to draw.
        glDrawArrays(GL_TRIANGLES, 0, N_VERTICES)

        glfw.swap_buffers(self.window)
        
    def maintainPaletteTable(self):
        # Note: only call this when self.bgVbo is bound to GL_ARRAY_BUFFER... maybe?
        if self.lastBgPalette != self.ppu.bgPatternTableAddr:
            
            self.patternTable = self.ppu.dumpPtab(self.ppu.bgPatternTableAddr)
            glBindTexture(GL_TEXTURE_2D_ARRAY, self.bgPtabName)
            glActiveTexture(BG_PATTERN_TABLE_TEXTURE)
            glTexImage3D(GL_TEXTURE_2D_ARRAY, 0, GL_RED, 8, 8, PATTERN_TABLE_TILES,
                         0, GL_RED, GL_UNSIGNED_BYTE, self.patternTable)
            self.lastBgPalette = self.ppu.bgPatternTableAddr
