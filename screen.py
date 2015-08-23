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

TILE_ROWS = ppu.VISIBLE_SCANLINES/8
TILE_COLUMNS = ppu.VISIBLE_COLUMNS/8

SCREEN_WIDTH = ppu.VISIBLE_COLUMNS
SCREEN_HEIGHT = ppu.VISIBLE_SCANLINES

N_VERTICES = TILE_ROWS * TILE_COLUMNS * 6

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

        in vec2 xy;
        in vec3 v_tuv;
        in uint v_palette_n;

        out vec2 f_uv;
        out vec4[4] f_palette;

        uniform vec4[16] localPalettes;

        void main()
        {
          gl_Position = vec4((float(xy.x) / 16.0) - 1, (float(xy.y) / 15.0) - 1, 0.0, 1.0);
          f_uv = vec2((float(v_tuv.y) / 256.0) + float(v_tuv.x) / 256.0, float(v_tuv.z));
          for (int i = 0; i < 4; i++) {
            f_palette[i] = localPalettes[i + int(v_palette_n)*4];
          }
        }"""
        vertexShader = shaders.compileShader(vertexShaderSrc, GL_VERTEX_SHADER)

        fragmentShaderSrc = """#version 330

        in vec2 f_uv;
        in vec4[4] f_palette;

        out vec4 outColor;

        uniform sampler2D patternTable;

        uniform float[16] localPalettes;

        void main()
        {
          float localPaletteIndex;
          localPaletteIndex = texture(patternTable, f_uv).r;
          // for now, assume localPaletteIndex will always be valid
          outColor = f_palette[int(localPaletteIndex)];
          outColor.a = 1.0;
        /*
          globalPaletteIndex = localPalettes[f_palette_n * 4 + localPaletteIndex];
          outColor = texture(globalPalette, globalPaletteIndex);
        */
        // DEBUG:
        /*
          float greyShade = localPaletteIndex / 4.0;
          outColor = vec4(greyShade, greyShade, greyShade, 1.0);
          //outColor = vec4(0.0, 0.0, 1.0, 1.0);
        */
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

        self.tileIndices = [[0 for y in range(TILE_ROWS)] for x in range(TILE_COLUMNS)]

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # TODO bind global palette

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
        (bg_r, bg_g, bg_b) = (128,128,255) # DEBUG
        glClearColor(bg_r / 255.0, bg_g / 255.0, bg_b / 255.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_ACCUM_BUFFER_BIT)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

        # TODO get rid of some of these magic numbers
        vertexList = [0 for x in range(TILE_COLUMNS * TILE_ROWS * 6 * 6)]
        # Note: x and y coordinates are in increments of tiles, so
        # they range from 0 to 32. This is a dumb hack because the
        # vertex shader was doing dumb things when I told it to divide
        # by 256, for reasons I don't understand.
        for x in xrange(TILE_COLUMNS):
            for y in xrange(TILE_ROWS):
                x_left = x
                x_right = x+1
                y_bottom = (TILE_ROWS - y - 1)
                y_top = (TILE_ROWS - y)
                tile = self.tileIndices[x][y]
                u_left = 0
                u_right = 1
                v_bottom = 1
                v_top = 0
                palette_index = 0 # TODO: determined by the pattern table
                screen_tile_index = (x + y*TILE_COLUMNS) * 6*6
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

        # FIXME magic number
        stride = 6 * ctypes.sizeof(ctypes.c_ubyte)

        glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(vertices), vertices, GL_DYNAMIC_DRAW)

        # TODO point attributes into that big buffer
        xyOffset = ctypes.c_void_p(0)
        glVertexAttribPointer(self.xyAttrib, 2, GL_UNSIGNED_BYTE, GL_FALSE, stride, xyOffset)
        glEnableVertexAttribArray(self.xyAttrib)
        tuvOffset = ctypes.c_void_p(2 * ctypes.sizeof(ctypes.c_ubyte))
        glVertexAttribPointer(self.tuvAttrib, 3, GL_UNSIGNED_BYTE, GL_FALSE, stride, tuvOffset)
        glEnableVertexAttribArray(self.tuvAttrib)
        # paletteNOffset = ctypes.c_void_p(5 * ctypes.sizeof(ctypes.c_ubyte))
        # glVertexAttribIPointer(self.paletteNAttrib, 1, GL_FLOAT, stride, paletteNOffset)
        # glEnableVertexAttribArray(self.paletteNAttrib)

        # point uniform arguments
        glUniform1i(glGetUniformLocation(self.shader, "patternTable"), BG_PATTERN_TABLE_TEXID)

        # and localPalettes.
        localPaletteList = self.ppu.dumpLocalPalettes(ppu.BG_PALETTE_BASE)
        print "localPaletteList[:16]:"
        print localPaletteList
        localPaletteCArray = (ctypes.c_float * len(localPaletteList)) (*localPaletteList)
        glUniform4fv(glGetUniformLocation(self.shader, "localPalettes"), 16, localPaletteCArray)

        # Finally, we should be able to draw.
        glDrawArrays(GL_TRIANGLES, 0, N_VERTICES)

        glfw.swap_buffers(self.window)

    def maintainPaletteTable(self):
        # Note: only call this when self.bgVbo is bound to GL_ARRAY_BUFFER... maybe?
        if self.lastBgPalette != self.ppu.bgPatternTableAddr:

            self.patternTable = self.ppu.dumpPtab(self.ppu.bgPatternTableAddr)
            # I can't make GL_R8UI work, so everything has to be floats
            patternTableFloats = [float(ord(x)) for x in self.patternTable]
            textureData = (ctypes.c_float * len(patternTableFloats)) (*patternTableFloats)
            glBindTexture(GL_TEXTURE_2D, self.bgPtabName)
            glActiveTexture(BG_PATTERN_TABLE_TEXTURE)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, 8*256, 8,
                         0, GL_RED, GL_FLOAT, textureData)
            self.lastBgPalette = self.ppu.bgPatternTableAddr
