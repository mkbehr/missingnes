"""Handle drawing objects to the screen. The code is seperate from
ppu.py because this doesn't handle the PPU's internal state - the view
to ppu.py's controller, let's say. (or is that the model? should we
have more separation?)

"""
import ctypes
import time

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

PROGRAM_NAME = "Missingnes"

TILE_ROWS = ppu.VISIBLE_SCANLINES/8
TILE_COLUMNS = ppu.VISIBLE_COLUMNS/8

SCREEN_WIDTH = ppu.VISIBLE_COLUMNS
SCREEN_HEIGHT = ppu.VISIBLE_SCANLINES

N_BG_VERTICES = TILE_ROWS * TILE_COLUMNS * 6

PATTERN_TABLE_TILES = 256

BG_PATTERN_TABLE_TEXTURE = GL_TEXTURE0
BG_PATTERN_TABLE_TEXID = 0
SPRITE_PATTERN_TABLE_TEXTURE = GL_TEXTURE1
SPRITE_PATTERN_TABLE_TEXID = 1
# TODO other texture ids go here

# number of values (elements) per vertex in the vertex buffer
VERTEX_ELTS = 7

DRAW_BG = True
DRAW_SPRITES = True

FPS_UPDATE_INTERVAL = 2.0 # in seconds
MAX_FPS = 60
SECONDS_PER_FRAME = 1.0 / MAX_FPS
FPS_TOLERANCE = 0.1

# gain determining seconds per frame (as in a kalman filter)
SPF_GAIN = 0.2

class Screen(object):

    def __init__(self, _ppu): # underscore to patch over sloppy naming hiding the ppu module

        self.ppu = _ppu


        if not glfw.init():
            assert(false) # fuck it

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3);
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 2);
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE);
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE);

        window = glfw.create_window(SCREEN_WIDTH, SCREEN_HEIGHT,
                                    "%s - (0) ?? FPS" % PROGRAM_NAME,
                                    None, None)
        self.window = window

        if not window:
            glfw.terminate()

        assert (glfw.get_window_attrib(window, glfw.CONTEXT_VERSION_MAJOR) >= 3)


        # Instead of just tracking keys, consider making sure
        # that when the user presses a button, that button is pressed
        # in the next frame, even if it's released before the frame is
        # processed.
        glfw.set_input_mode(window, glfw.STICKY_KEYS, 1)


        vao_id = GLuint(0)
        # use pyglet because pyopengl doesn't like these functions
        pyglet.gl.glGenVertexArrays(1, ctypes.byref(vao_id))
        pyglet.gl.glBindVertexArray(vao_id.value)

        # The x_high here is because x can reach 256, so we need an
        # extra byte to stop it from wrapping around to 0.
        vertexShaderSrc = """#version 330

        in vec2 xy;
        in float x_high;
        in vec3 v_tuv;
        in uint v_palette_n;

        out vec2 f_uv;
        out vec4[4] f_palette;

        uniform vec4[16] localPalettes;

        void main()
        {
          gl_Position = vec4(((float(xy.x) + (x_high * 256)) / (16.0*8.0)) - 1,
                             (float(xy.y) / (15.0*8.0)) - 1, 0.0, 1.0);
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
        }"""
        fragmentShader = shaders.compileShader(fragmentShaderSrc, GL_FRAGMENT_SHADER)
        self.shader = shaders.compileProgram(vertexShader, fragmentShader)
        glUseProgram(self.shader)

        self.xyAttrib = glGetAttribLocation(self.shader, "xy")
        self.xHighAttrib = glGetAttribLocation(self.shader, "x_high");
        self.tuvAttrib = glGetAttribLocation(self.shader, "v_tuv")
        self.paletteNAttrib = glGetAttribLocation(self.shader, "v_palette_n")

        self.lastBgPalette = None
        self.lastSpritePalette = None

        self.bgVbo = glGenBuffers(1)
        self.spriteVbo = glGenBuffers(1)

        self.bgPtabName = glGenTextures(1)
        self.spritePtabName = glGenTextures(1)

        self.tileIndices = [[0 for y in range(TILE_ROWS)] for x in range(TILE_COLUMNS)]
        self.paletteIndices = [[0 for y in range(TILE_ROWS)] for x in range(TILE_COLUMNS)]

        bgVertexList = [0 for x in range(TILE_COLUMNS * TILE_ROWS * VERTEX_ELTS * 6)]
        self.bgVertices = (ctypes.c_ubyte * len(bgVertexList)) (*bgVertexList)
        # Set x, y, u, and v coordinates, because they won't change.

        # Note: x and y coordinates are pixel coordinates, but we need
        # to store an extra byte for the x coordinate because it can
        # range from 0 to 256 inclusive.
        for x in xrange(TILE_COLUMNS):
            for y in xrange(TILE_ROWS):
                x_left = x*8
                x_right = (x+1)*8
                x_left_high = 0
                if x_right == 256:
                    x_right = 0
                    x_right_high = 1
                else:
                    x_right_high = 0
                y_bottom = (TILE_ROWS - y - 1)*8
                y_top = (TILE_ROWS - y)*8
                tile = 0 # this will change
                u_left = 0
                u_right = 1
                v_bottom = 1
                v_top = 0
                palette_index = 0 # this will change
                screen_tile_index = (x + y*TILE_COLUMNS) * VERTEX_ELTS * 6
                self.bgVertices[screen_tile_index : (screen_tile_index+(VERTEX_ELTS*6))] = [
                    # do this as two triangles
                    # first triangle
                    x_left, y_bottom, x_left_high, tile, u_left, v_bottom, palette_index,
                    x_right, y_bottom, x_right_high, tile, u_right, v_bottom, palette_index,
                    x_right, y_top, x_right_high, tile, u_right, v_top, palette_index,
                    # second triangle
                    x_left, y_bottom, x_left_high, tile, u_left, v_bottom, palette_index,
                    x_right, y_top, x_right_high, tile, u_right, v_top, palette_index,
                    x_left, y_top, x_left_high, tile, u_left, v_top, palette_index,
                    ]

        self.fpsLastUpdated = None
        self.fpsLastTime = 0
        self.fpsLastDisplayed = 0
        self.secondsPerFrame = None

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # TODO bind global palette

    def tick(self, frame): # TODO consider turning this into a more general callback that the ppu gets
        self.draw_to_buffer()

        # Handle controller input.

        glfw.poll_events()

        # TODO: use fewer magic numbers and put together a proper
        # structure for this code.

        # forgive me demeter for I have sinned
        ips = self.ppu.cpu.controller.inputState.states

        ips[0] = self.pollKey(glfw.KEY_A) # A
        ips[1] = self.pollKey(glfw.KEY_S) # B
        ips[2] = self.pollKey(glfw.KEY_BACKSLASH) # select: mapping to \ for now
        ips[3] = self.pollKey(glfw.KEY_ENTER) # start
        ips[4] = self.pollKey(glfw.KEY_UP) # up
        ips[5] = self.pollKey(glfw.KEY_DOWN) # down
        ips[6] = self.pollKey(glfw.KEY_LEFT) # left
        ips[7] = self.pollKey(glfw.KEY_RIGHT) # right

        timenow = time.clock()
        if timenow < self.fpsLastTime + SECONDS_PER_FRAME * (1.0 - FPS_TOLERANCE):
            time.sleep(self.fpsLastTime + SECONDS_PER_FRAME - timenow)
            timenow = time.clock()

        if self.secondsPerFrame is not None:
            observedSpf = (timenow - self.fpsLastTime) / (frame - self.fpsLastUpdated)
            self.secondsPerFrame = (SPF_GAIN * observedSpf +
                                    (1 - SPF_GAIN) * self.secondsPerFrame)
        elif self.fpsLastUpdated is not None:
            observedSpf = (timenow - self.fpsLastTime) / (frame - self.fpsLastUpdated)
            self.secondsPerFrame = observedSpf
        self.fpsLastUpdated = frame
        self.fpsLastTime = timenow
        if timenow >= self.fpsLastDisplayed + FPS_UPDATE_INTERVAL:
            if self.secondsPerFrame is not None:
                glfw.set_window_title(self.window,
                                      "%s - (%d) %d FPS" % (PROGRAM_NAME, frame, 1.0/self.secondsPerFrame))
            self.fpsLastDisplayed = timenow

        glfw.swap_buffers(self.window)


    def draw_to_buffer(self):
        (bg_r, bg_g, bg_b) = palette.PALETTE[self.ppu.universalBg]
        glClearColor(bg_r / 255.0, bg_g / 255.0, bg_b / 255.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_ACCUM_BUFFER_BIT)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

        if DRAW_BG:
            glBindBuffer(GL_ARRAY_BUFFER, self.bgVbo)

            # We need to do this here (anytime before the draw call) and I
            # don't really understand why. The order is important for some
            # reason.
            glActiveTexture(BG_PATTERN_TABLE_TEXTURE)
            glBindTexture(GL_TEXTURE_2D, self.bgPtabName)

            self.maintainBgPaletteTable()

            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

            # TODO get rid of some of these magic numbers

            # Set tile and palette. The rest of the values in the VBO won't change.
            for x in xrange(TILE_COLUMNS):
                for y in xrange(TILE_ROWS):
                    tile = self.tileIndices[x][y]
                    palette_index = self.paletteIndices[x][y]
                    screen_tile_index = (x + y*TILE_COLUMNS) * VERTEX_ELTS*6
                    for vertex_i in range(6):
                        self.bgVertices[screen_tile_index + vertex_i*VERTEX_ELTS + 3] = tile
                        self.bgVertices[screen_tile_index + vertex_i*VERTEX_ELTS + 6] = palette_index

            stride = VERTEX_ELTS * ctypes.sizeof(ctypes.c_ubyte)

            glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(self.bgVertices), self.bgVertices, GL_DYNAMIC_DRAW)

            # point attributes into that big buffer
            xyOffset = ctypes.c_void_p(0)
            glVertexAttribPointer(self.xyAttrib, 2, GL_UNSIGNED_BYTE, GL_FALSE, stride, xyOffset)
            glEnableVertexAttribArray(self.xyAttrib)
            xHighOffset = ctypes.c_void_p(2 * ctypes.sizeof(ctypes.c_ubyte))
            glVertexAttribPointer(self.xHighAttrib, 1, GL_UNSIGNED_BYTE, GL_FALSE, stride, xHighOffset)
            glEnableVertexAttribArray(self.xHighAttrib)
            tuvOffset = ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_ubyte))
            glVertexAttribPointer(self.tuvAttrib, 3, GL_UNSIGNED_BYTE, GL_FALSE, stride, tuvOffset)
            glEnableVertexAttribArray(self.tuvAttrib)
            paletteNOffset = ctypes.c_void_p(6 * ctypes.sizeof(ctypes.c_ubyte))
            glVertexAttribIPointer(self.paletteNAttrib, 1, GL_UNSIGNED_BYTE, stride, paletteNOffset)
            glEnableVertexAttribArray(self.paletteNAttrib)

            # point uniform arguments
            glUniform1i(glGetUniformLocation(self.shader, "patternTable"), BG_PATTERN_TABLE_TEXID)

            # and localPalettes.
            localPaletteList = self.ppu.dumpLocalPalettes(ppu.BG_PALETTE_BASE)
            localPaletteCArray = (ctypes.c_float * len(localPaletteList)) (*localPaletteList)
            glUniform4fv(glGetUniformLocation(self.shader, "localPalettes"), 16, localPaletteCArray)

            # Finally, we should be able to draw.
            glDrawArrays(GL_TRIANGLES, 0, N_BG_VERTICES)

        ## Now do sprites.
        if DRAW_SPRITES:
            glBindBuffer(GL_ARRAY_BUFFER, self.spriteVbo)

            # as with the calls to these in the bg code, I don't know why
            # we need these but we do
            glActiveTexture(SPRITE_PATTERN_TABLE_TEXTURE)
            glBindTexture(GL_TEXTURE_2D, self.spritePtabName)

            self.maintainSpritePaletteTable()

            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

            nSpriteVertices = 0
            spriteVertexList = []

            oam = self.ppu.oam
            for i in range(ppu.OAM_SIZE / ppu.OAM_ENTRY_SIZE):
                # TODO deal with maximum sprites per scanline
                baseindex = i * ppu.OAM_ENTRY_SIZE
                spritetop = ord(oam[baseindex]) + 1
                if spritetop >= 0xf0: # the sprite is wholly off the screen; ignore it
                    continue
                # TODO account for 8x16 sprites

                tile = ord(oam[baseindex+1])
                attributes = ord(oam[baseindex+2])
                spriteleft = ord(oam[baseindex+3])
                palette_index = attributes & 0x3
                horizontalMirror = bool(attributes & 0x40)
                verticalMirror = bool(attributes & 0x80)

                spritebottom = spritetop+8
                spriteright = spriteleft+8

                x_left = spriteleft
                x_right = spriteright % 256
                x_left_high = 0
                x_right_high = spriteright / 256

                y_top = SCREEN_HEIGHT - spritetop
                y_bottom = SCREEN_HEIGHT - spritebottom

                if horizontalMirror:
                    u_left = 1
                    u_right = 0
                else:
                    u_left = 0
                    u_right = 1

                if verticalMirror:
                    v_bottom = 0
                    v_top = 1
                else:
                    v_bottom = 1
                    v_top = 0

                spriteVertexList += [
                    # first triangle
                    x_left, y_bottom, x_left_high, tile, u_left, v_bottom, palette_index,
                    x_right, y_bottom, x_right_high, tile, u_right, v_bottom, palette_index,
                    x_right, y_top, x_right_high, tile, u_right, v_top, palette_index,
                    # second triangle
                    x_left, y_bottom, x_left_high, tile, u_left, v_bottom, palette_index,
                    x_right, y_top, x_right_high, tile, u_right, v_top, palette_index,
                    x_left, y_top, x_left_high, tile, u_left, v_top, palette_index,
                    ]
                nSpriteVertices += 6

            # TODO: we can go a bit faster by not recreating this and just
            # trusting our vertex count to prevent us from drawing garbage
            # data
            spriteVertices = (ctypes.c_ubyte * len(spriteVertexList)) (*spriteVertexList)

            stride = VERTEX_ELTS * ctypes.sizeof(ctypes.c_ubyte)

            glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(self.bgVertices), spriteVertices, GL_DYNAMIC_DRAW)

            # Pointing attributes should work the same as with the bg
            # code. I'm not sure we even need to repeat this code. Only
            # difference is that the pattern table and palettes are
            # different.

            # point attributes into that big buffer
            xyOffset = ctypes.c_void_p(0)
            glVertexAttribPointer(self.xyAttrib, 2, GL_UNSIGNED_BYTE, GL_FALSE, stride, xyOffset)
            glEnableVertexAttribArray(self.xyAttrib)
            xHighOffset = ctypes.c_void_p(2 * ctypes.sizeof(ctypes.c_ubyte))
            glVertexAttribPointer(self.xHighAttrib, 1, GL_UNSIGNED_BYTE, GL_FALSE, stride, xHighOffset)
            glEnableVertexAttribArray(self.xHighAttrib)
            tuvOffset = ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_ubyte))
            glVertexAttribPointer(self.tuvAttrib, 3, GL_UNSIGNED_BYTE, GL_FALSE, stride, tuvOffset)
            glEnableVertexAttribArray(self.tuvAttrib)
            paletteNOffset = ctypes.c_void_p(6 * ctypes.sizeof(ctypes.c_ubyte))
            glVertexAttribIPointer(self.paletteNAttrib, 1, GL_UNSIGNED_BYTE, stride, paletteNOffset)
            glEnableVertexAttribArray(self.paletteNAttrib)

            # point uniform arguments
            glUniform1i(glGetUniformLocation(self.shader, "patternTable"), SPRITE_PATTERN_TABLE_TEXID)

            # and localPalettes.
            localPaletteList = self.ppu.dumpLocalPalettes(ppu.SPRITE_PALETTE_BASE)
            localPaletteCArray = (ctypes.c_float * len(localPaletteList)) (*localPaletteList)
            glUniform4fv(glGetUniformLocation(self.shader, "localPalettes"), 16, localPaletteCArray)

            # And now we can draw and hope for the best.
            glDrawArrays(GL_TRIANGLES, 0, nSpriteVertices)

        # Don't swap buffers here; wait until we've had a chance to sleep in order to cap FPS

        # glfw.swap_buffers(self.window)

    def maintainBgPaletteTable(self):
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

    def maintainSpritePaletteTable(self):
        # I think this wants self.spriteVbo to be bound to GL_ARRAY_BUFFER
        if self.lastSpritePalette != self.ppu.spritePatternTableAddr:

            self.patternTable = self.ppu.dumpPtab(self.ppu.spritePatternTableAddr)
            # I can't make GL_R8UI work, so everything has to be floats
            patternTableFloats = [float(ord(x)) for x in self.patternTable]
            textureData = (ctypes.c_float * len(patternTableFloats)) (*patternTableFloats)
            glBindTexture(GL_TEXTURE_2D, self.spritePtabName)
            glActiveTexture(SPRITE_PATTERN_TABLE_TEXTURE)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, 8*256, 8,
                         0, GL_RED, GL_FLOAT, textureData)
            self.lastSpritePalette = self.ppu.spritePatternTableAddr

    def pollKey(self, key):
        return glfw.get_key(self.window, key) == glfw.PRESS
