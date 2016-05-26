"""Handle drawing objects to the screen. The code is seperate from
ppu.py because this doesn't handle the PPU's internal state - the view
to ppu.py's controller, let's say. (or is that the model? should we
have more separation?)

"""
import ctypes
import threading
import time

import numpy as np

import palette
import ppu

import libscreen

PROGRAM_NAME = "Missingnes"

TILE_ROWS = ppu.VISIBLE_SCANLINES/8
TILE_COLUMNS = ppu.VISIBLE_COLUMNS/8

SCREEN_WIDTH = ppu.VISIBLE_COLUMNS
SCREEN_HEIGHT = ppu.VISIBLE_SCANLINES

N_BG_VERTICES = TILE_ROWS * TILE_COLUMNS * 6

PATTERN_TABLE_TILES = 256

# BG_PATTERN_TABLE_TEXTURE = GL_TEXTURE0
# BG_PATTERN_TABLE_TEXID = 0
# SPRITE_PATTERN_TABLE_TEXTURE = GL_TEXTURE1
# SPRITE_PATTERN_TABLE_TEXID = 1
# TODO other texture ids go here

# number of values (elements) per vertex in the vertex buffer
VERTEX_ELTS = 7

DRAW_BG = True
DRAW_SPRITES = False

FPS_UPDATE_INTERVAL = 2.0 # in seconds
MAX_FPS = 60
SECONDS_PER_FRAME = 1.0 / MAX_FPS

# gain determining seconds per frame (as in a kalman filter)
SPF_GAIN = 0.2

class Screen(object):

    def __init__(self, _ppu): # underscore to patch over sloppy naming hiding the ppu module

        self.ppu = _ppu

        self.lastBgPattern = None
        self.lastSpritePattern = None

        self.tileIndices = [[0 for y in range(TILE_ROWS)] for x in range(TILE_COLUMNS)]
        self.paletteIndices = [[0 for y in range(TILE_ROWS)] for x in range(TILE_COLUMNS)]

        self.fpsLastUpdated = None
        self.fpsLastTime = 0
        self.fpsLastDisplayed = 0
        self.secondsPerFrame = None

        self.cscreen = libscreen.Screen()

    def tick(self, frame): # TODO consider turning this into a more general callback that the ppu gets
        self.draw_to_buffer()

        # TODO reinstate FPS-capping code
        self.cscreen.draw()

        # time.sleep(1)

        return

        # Handle controller input.

        #glfw.poll_events()

        # TODO: use fewer magic numbers and put together a proper
        # structure for this code.

        # forgive me demeter for I have sinned
        ips = self.ppu.cpu.controller.inputState.states

        # ips[0] = self.pollKey(glfw.KEY_A) # A
        # ips[1] = self.pollKey(glfw.KEY_S) # B
        # ips[2] = self.pollKey(glfw.KEY_BACKSLASH) # select: mapping to \ for now
        # ips[3] = self.pollKey(glfw.KEY_ENTER) # start
        # ips[4] = self.pollKey(glfw.KEY_UP) # up
        # ips[5] = self.pollKey(glfw.KEY_DOWN) # down
        # ips[6] = self.pollKey(glfw.KEY_LEFT) # left
        # ips[7] = self.pollKey(glfw.KEY_RIGHT) # right

        timenow = time.time()

        # if self.secondsPerFrame is not None:
        #     # this causes segafaults and I don't know why:

        #     # if self.secondsPerFrame < SECONDS_PER_FRAME:
        #     #     targetTime = timenow + SECONDS_PER_FRAME - self.secondsPerFrame
        #     #     time.sleep(targetTime - timenow)
        #     #     timenow = time.time()
        #     observedSpf = (timenow - self.fpsLastTime) / (frame - self.fpsLastUpdated)
        #     self.secondsPerFrame = (SPF_GAIN * observedSpf +
        #                             (1 - SPF_GAIN) * self.secondsPerFrame)
        # elif self.fpsLastUpdated is not None:
        #     observedSpf = (timenow - self.fpsLastTime) / (frame - self.fpsLastUpdated)
        #     self.secondsPerFrame = observedSpf
        # self.fpsLastUpdated = frame
        # self.fpsLastTime = timenow
        # if timenow >= self.fpsLastDisplayed + FPS_UPDATE_INTERVAL:
        #     if self.secondsPerFrame is not None:
        #         glfw.set_window_title(self.window,
        #                               "%s - (%d) %d FPS" % (PROGRAM_NAME, frame, 1.0/self.secondsPerFrame))
        #     self.fpsLastDisplayed = timenow

        # self.gpuStart.set()


    def draw_to_buffer(self):
        self.cscreen.setUniversalBg(self.ppu.universalBg)

        if DRAW_BG:

            self.maintainBgPatternTable()

            self.cscreen.setTileIndices(self.tileIndices)
            self.cscreen.setPaletteIndices(self.paletteIndices)

            # Set tile and palette. The rest of the values in the VBO won't change.
            for x in xrange(TILE_COLUMNS):
                for y in xrange(TILE_ROWS):
                    tile = self.tileIndices[x][y]
                    palette_index = self.paletteIndices[x][y]
                    screen_tile_index = (x + y*TILE_COLUMNS) * VERTEX_ELTS*6
                    # for vertex_i in range(6):
                    #     self.bgVertices[screen_tile_index + vertex_i*VERTEX_ELTS + 3] = tile
                    #     self.bgVertices[screen_tile_index + vertex_i*VERTEX_ELTS + 6] = palette_index

            # stride = VERTEX_ELTS * ctypes.sizeof(ctypes.c_ubyte)

            # glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(self.bgVertices), self.bgVertices, GL_DYNAMIC_DRAW)
            localPaletteList = self.ppu.dumpLocalPalettes(ppu.BG_PALETTE_BASE)
            self.cscreen.setLocalPalettes(localPaletteList)
            # print self.paletteIndices
            # localPaletteNums = [0 for i in range(16)]
            # for i in range(16):
            #     if (i % 4) == 0:
            #         continue
            #     localPaletteNums[i] = ord(self.ppu.cpu.mem.ppuRead(ppu.BG_PALETTE_BASE + i))
            # print localPaletteNums
            # print localPaletteList

        self.cscreen.drawToBuffer()

        ## Now do sprites.
        if DRAW_SPRITES:
            # glBindBuffer(GL_ARRAY_BUFFER, self.spriteVbo)

            # # as with the calls to these in the bg code, I don't know why
            # # we need these but we do
            # glActiveTexture(SPRITE_PATTERN_TABLE_TEXTURE)
            # glBindTexture(GL_TEXTURE_2D, self.spritePtabName)

            # self.maintainSpritePatternTable()

            # glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
            # glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);

            # nSpriteVertices = 0
            # spriteVertexList = []

            # oam = self.ppu.oam
            # for i in range(ppu.OAM_SIZE / ppu.OAM_ENTRY_SIZE):
            #     # TODO deal with maximum sprites per scanline
            #     baseindex = i * ppu.OAM_ENTRY_SIZE
            #     spritetop = ord(oam[baseindex]) + 1
            #     if spritetop >= 0xf0: # the sprite is wholly off the screen; ignore it
            #         continue
            #     # TODO account for 8x16 sprites

            #     tile = ord(oam[baseindex+1])
            #     attributes = ord(oam[baseindex+2])
            #     spriteleft = ord(oam[baseindex+3])
            #     palette_index = attributes & 0x3
            #     horizontalMirror = bool(attributes & 0x40)
            #     verticalMirror = bool(attributes & 0x80)

            #     spritebottom = spritetop+8
            #     spriteright = spriteleft+8

            #     x_left = spriteleft
            #     x_right = spriteright % 256
            #     x_left_high = 0
            #     x_right_high = spriteright / 256

            #     y_top = SCREEN_HEIGHT - spritetop
            #     y_bottom = SCREEN_HEIGHT - spritebottom

            #     if horizontalMirror:
            #         u_left = 1
            #         u_right = 0
            #     else:
            #         u_left = 0
            #         u_right = 1

            #     if verticalMirror:
            #         v_bottom = 0
            #         v_top = 1
            #     else:
            #         v_bottom = 1
            #         v_top = 0

            #     spriteVertexList += [
            #         # first triangle
            #         x_left, y_bottom, x_left_high, tile, u_left, v_bottom, palette_index,
            #         x_right, y_bottom, x_right_high, tile, u_right, v_bottom, palette_index,
            #         x_right, y_top, x_right_high, tile, u_right, v_top, palette_index,
            #         # second triangle
            #         x_left, y_bottom, x_left_high, tile, u_left, v_bottom, palette_index,
            #         x_right, y_top, x_right_high, tile, u_right, v_top, palette_index,
            #         x_left, y_top, x_left_high, tile, u_left, v_top, palette_index,
            #         ]
            #     nSpriteVertices += 6
            pass

            # TODO: we can go a bit faster by not recreating this and just
            # trusting our vertex count to prevent us from drawing garbage
            # data
            # spriteVertices = (ctypes.c_ubyte * len(spriteVertexList)) (*spriteVertexList)

            # stride = VERTEX_ELTS * ctypes.sizeof(ctypes.c_ubyte)

            # glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(self.bgVertices), spriteVertices, GL_DYNAMIC_DRAW)

            # # Pointing attributes should work the same as with the bg
            # # code. I'm not sure we even need to repeat this code. Only
            # # difference is that the pattern table and palettes are
            # # different.

            # # point attributes into that big buffer
            # xyOffset = ctypes.c_void_p(0)
            # glVertexAttribPointer(self.xyAttrib, 2, GL_UNSIGNED_BYTE, GL_FALSE, stride, xyOffset)
            # glEnableVertexAttribArray(self.xyAttrib)
            # xHighOffset = ctypes.c_void_p(2 * ctypes.sizeof(ctypes.c_ubyte))
            # glVertexAttribPointer(self.xHighAttrib, 1, GL_UNSIGNED_BYTE, GL_FALSE, stride, xHighOffset)
            # glEnableVertexAttribArray(self.xHighAttrib)
            # tuvOffset = ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_ubyte))
            # glVertexAttribPointer(self.tuvAttrib, 3, GL_UNSIGNED_BYTE, GL_FALSE, stride, tuvOffset)
            # glEnableVertexAttribArray(self.tuvAttrib)
            # paletteNOffset = ctypes.c_void_p(6 * ctypes.sizeof(ctypes.c_ubyte))
            # glVertexAttribIPointer(self.paletteNAttrib, 1, GL_UNSIGNED_BYTE, stride, paletteNOffset)
            # glEnableVertexAttribArray(self.paletteNAttrib)

            # # point uniform arguments
            # glUniform1i(glGetUniformLocation(self.shader, "patternTable"), SPRITE_PATTERN_TABLE_TEXID)

            # # and localPalettes.
            # localPaletteList = self.ppu.dumpLocalPalettes(ppu.SPRITE_PALETTE_BASE)
            # localPaletteCArray = (ctypes.c_float * len(localPaletteList)) (*localPaletteList)
            # glUniform4fv(glGetUniformLocation(self.shader, "localPalettes"), 16, localPaletteCArray)

            # # And now we can draw and hope for the best.
            # glDrawArrays(GL_TRIANGLES, 0, nSpriteVertices)

        # Don't swap buffers here; wait until we've had a chance to sleep in order to cap FPS

        # glfw.swap_buffers(self.window)

    def maintainBgPatternTable(self):
        if self.lastBgPattern != self.ppu.bgPatternTableAddr:

            self.patternTable = self.ppu.dumpPtab(self.ppu.bgPatternTableAddr)
            # # I can't make GL_R8UI work, so everything has to be floats
            patternTableFloats = [float(ord(x)) for x in self.patternTable]
            self.cscreen.setBgPatternTable(patternTableFloats);

            # textureData = (ctypes.c_float * len(patternTableFloats)) (*patternTableFloats)
            # glBindTexture(GL_TEXTURE_2D, self.bgPtabName)
            # glActiveTexture(BG_PATTERN_TABLE_TEXTURE)
            # glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, 8*256, 8,
            #              0, GL_RED, GL_FLOAT, textureData)
            # self.lastBgPattern = self.ppu.bgPatternTableAddr

    def maintainSpritePatternTable(self):
        # I think this wants self.spriteVbo to be bound to GL_ARRAY_BUFFER
        if self.lastSpritePattern != self.ppu.spritePatternTableAddr:

            self.patternTable = self.ppu.dumpPtab(self.ppu.spritePatternTableAddr)
            # I can't make GL_R8UI work, so everything has to be floats
            patternTableFloats = [float(ord(x)) for x in self.patternTable]
            textureData = (ctypes.c_float * len(patternTableFloats)) (*patternTableFloats)
            glBindTexture(GL_TEXTURE_2D, self.spritePtabName)
            glActiveTexture(SPRITE_PATTERN_TABLE_TEXTURE)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, 8*256, 8,
                         0, GL_RED, GL_FLOAT, textureData)
            self.lastSpritePattern = self.ppu.spritePatternTableAddr

    def pollKey(self, key):
        return glfw.get_key(self.window, key) == glfw.PRESS

class GPUThread(threading.Thread):
    def __init__(self, window, gpuStart, gpuDone):
        threading.Thread.__init__(self)
        self.window = window
        self.gpuStart = gpuStart
        self.gpuDone = gpuDone

    def run(self):
        while True:
            self.gpuStart.wait()
            self.gpuStart.clear()
            glfw.swap_buffers(self.window)
            self.gpuDone.set()
