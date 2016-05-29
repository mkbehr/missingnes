"""Handle drawing objects to the screen. The code is seperate from
ppu.py because this doesn't handle the PPU's internal state - the view
to ppu.py's controller, let's say. (or is that the model? should we
have more separation?)

"""
import ctypes
from ctypes import CDLL, c_void_p, c_int, c_float, c_ubyte
import threading
import time
import sys

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
PATTERN_TABLE_ENTRIES = 8*8*PATTERN_TABLE_TILES

# BG_PATTERN_TABLE_TEXTURE = GL_TEXTURE0
# BG_PATTERN_TABLE_TEXID = 0
# SPRITE_PATTERN_TABLE_TEXTURE = GL_TEXTURE1
# SPRITE_PATTERN_TABLE_TEXID = 1
# TODO other texture ids go here

LOCAL_PALETTES_LENGTH = 16*4

# number of values (elements) per vertex in the vertex buffer
VERTEX_ELTS = 7

DRAW_BG = True
DRAW_SPRITES = True

FPS_UPDATE_INTERVAL = 2.0 # in seconds
MAX_FPS = 60
SECONDS_PER_FRAME = 1.0 / MAX_FPS

# gain determining seconds per frame (as in a kalman filter)
SPF_GAIN = 0.2

KEY_MASK_A = 1<<0;
KEY_MASK_B = 1<<1;
KEY_MASK_SELECT = 1<<2;
KEY_MASK_START = 1<<3;
KEY_MASK_UP = 1<<4;
KEY_MASK_DOWN = 1<<5;
KEY_MASK_LEFT = 1<<6;
KEY_MASK_RIGHT = 1<<7;

def trace(func):
    fname = func.func_name
    def out(*args,**kwargs):
        print >> sys.stderr, ("Entering %s" % fname)
        val = func(*args,**kwargs)
        print >> sys.stderr, ("Leaving %s" % fname)
    return out

class CScreen(object):
    # Is this the best interface structure? Eh, it'll work.

    def __init__(self):
        libscreen = CDLL("libscreen.so")
        libscreen.ex_constructScreen.restype = c_void_p

        libscreen.ex_setUniversalBg.argtypes = [c_void_p, c_int]

        libscreen.ex_drawToBuffer.argtypes = [c_void_p]

        libscreen.ex_setBgPalettes.argtypes = \
        [c_void_p, (c_float * LOCAL_PALETTES_LENGTH)]

        libscreen.ex_setSpritePalettes.argtypes = \
        [c_void_p, (c_float * LOCAL_PALETTES_LENGTH)]

        libscreen.ex_setBgPatternTable.argtypes = \
        [c_void_p, (c_float * PATTERN_TABLE_ENTRIES)]

        libscreen.ex_setSpritePatternTable.argtypes = \
        [c_void_p, (c_float * PATTERN_TABLE_ENTRIES)]

        libscreen.ex_setTileIndices.argtypes = \
        [c_void_p, c_ubyte * (TILE_ROWS * TILE_COLUMNS)]

        libscreen.ex_setPaletteIndices.argtypes = \
        [c_void_p, c_ubyte * (TILE_ROWS * TILE_COLUMNS)]

        libscreen.ex_setOam.argtypes = \
        [c_void_p, c_ubyte * ppu.OAM_SIZE]

        libscreen.ex_draw.argtypes = [c_void_p]
        libscreen.ex_draw.restype = c_int

        libscreen.ex_pollKeys.argtypes = [c_void_p]
        libscreen.ex_pollKeys.restype = c_ubyte

        self.libscreen = libscreen

        self.screen_p = libscreen.ex_constructScreen()

    def setUniversalBg(self, bg):
        self.libscreen.ex_setUniversalBg(self.screen_p, bg)

    def setBgPalettes(self, paletteInput):
        # This takes in a list and handles type conversion itself.
        assert(len(paletteInput) == LOCAL_PALETTES_LENGTH)
        c_paletteInput = (c_float * LOCAL_PALETTES_LENGTH) (*paletteInput)
        self.libscreen.ex_setBgPalettes(self.screen_p, c_paletteInput)

    def setSpritePalettes(self, paletteInput):
        assert(len(paletteInput) == LOCAL_PALETTES_LENGTH)
        c_paletteInput = (c_float * LOCAL_PALETTES_LENGTH) (*paletteInput)
        self.libscreen.ex_setSpritePalettes(self.screen_p, c_paletteInput)

    def setBgPatternTable(self, bgInput):
        assert(len(bgInput) == PATTERN_TABLE_ENTRIES)
        c_ptab = (c_float * PATTERN_TABLE_ENTRIES) (*bgInput)
        self.libscreen.ex_setBgPatternTable(self.screen_p, c_ptab)

    def setSpritePatternTable(self, spriteInput):
        assert(len(spriteInput) == PATTERN_TABLE_ENTRIES)
        c_ptab = (c_float * PATTERN_TABLE_ENTRIES) (*spriteInput)
        self.libscreen.ex_setSpritePatternTable(self.screen_p, c_ptab)

    def setTileIndices(self, indices):
        assert(len(indices) == TILE_COLUMNS)
        intermediate = []
        for column in indices:
            assert len(column) == TILE_ROWS
            intermediate += column
        c_indices = (c_ubyte * (TILE_ROWS * TILE_COLUMNS)) (*intermediate)
        self.libscreen.ex_setTileIndices(self.screen_p, c_indices)

    def setPaletteIndices(self, indices):
        assert(len(indices) == TILE_COLUMNS)
        intermediate = []
        for column in indices:
            assert len(column) == TILE_ROWS
            intermediate += column
        c_indices = (c_ubyte * (TILE_ROWS * TILE_COLUMNS)) (*intermediate)
        self.libscreen.ex_setPaletteIndices(self.screen_p, c_indices)

    def setOam(self, oamBytes):
        assert(len(oamBytes) == ppu.OAM_SIZE)
        c_oamBytes = (c_ubyte * ppu.OAM_SIZE) (*oamBytes)
        self.libscreen.ex_setOam(self.screen_p, c_oamBytes)

    def drawToBuffer(self):
        self.libscreen.ex_drawToBuffer(self.screen_p)

    def draw(self):
        return self.libscreen.ex_draw(self.screen_p)

    def pollKeys(self):
        return self.libscreen.ex_pollKeys(self.screen_p)


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

        self.cscreen = CScreen()

    def tick(self, frame): # TODO consider turning this into a more general callback that the ppu gets
        self.draw_to_buffer()

        # TODO reinstate FPS-capping code
        drawval = self.cscreen.draw()
        if drawval != 0:
            sys.exit(0)

        # time.sleep(1)

        # Handle controller input.

        #glfw.poll_events()

        # TODO: use fewer magic numbers and put together a proper
        # structure for this code.

        # # forgive me demeter for I have sinned
        ips = self.ppu.cpu.controller.inputState.states

        keys = self.cscreen.pollKeys()

        ips[0] = bool(keys & KEY_MASK_A) # A: A
        ips[1] = bool(keys & KEY_MASK_B) # B: S
        ips[2] = bool(keys & KEY_MASK_SELECT) # Select: \
        ips[3] = bool(keys & KEY_MASK_START) # Start: Enter
        ips[4] = bool(keys & KEY_MASK_UP) # Up: Up
        ips[5] = bool(keys & KEY_MASK_DOWN) # Down: Down
        ips[6] = bool(keys & KEY_MASK_LEFT) # Left: Left
        ips[7] = bool(keys & KEY_MASK_RIGHT) # Right: Right

        timenow = time.time()

        if self.secondsPerFrame is not None:
            # this causes segfaults and I don't know why:

            # if self.secondsPerFrame < SECONDS_PER_FRAME:
            #     targetTime = timenow + SECONDS_PER_FRAME - self.secondsPerFrame
            #     time.sleep(targetTime - timenow)
            #     timenow = time.time()
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
                print "Frame %d (%d FPS)" % (frame, 1.0 / self.secondsPerFrame)
                # glfw.set_window_title(self.window,
                #                       "%s - (%d) %d FPS" % (PROGRAM_NAME, frame, 1.0/self.secondsPerFrame))
            self.fpsLastDisplayed = timenow

        # self.gpuStart.set()


    def draw_to_buffer(self):
        self.cscreen.setUniversalBg(self.ppu.universalBg)

        if DRAW_BG:
            self.maintainBgPatternTable()
            self.cscreen.setTileIndices(self.tileIndices)
            self.cscreen.setPaletteIndices(self.paletteIndices)
            localPaletteList = self.ppu.dumpLocalPalettes(ppu.BG_PALETTE_BASE)
            self.cscreen.setBgPalettes(localPaletteList)
        ## Now do sprites.
        if DRAW_SPRITES:
            self.maintainSpritePatternTable()
            localPaletteList = self.ppu.dumpLocalPalettes(ppu.SPRITE_PALETTE_BASE)
            self.cscreen.setSpritePalettes(localPaletteList)
            self.cscreen.setOam([ord(x) for x in self.ppu.oam])
        self.cscreen.drawToBuffer()

    def maintainBgPatternTable(self):
        if self.lastBgPattern != self.ppu.bgPatternTableAddr:
            self.bgPatternTable = self.ppu.dumpPtab(self.ppu.bgPatternTableAddr)
            # # I can't make GL_R8UI work, so everything has to be floats
            patternTableFloats = [float(ord(x)) for x in self.bgPatternTable]
            self.cscreen.setBgPatternTable(patternTableFloats)
            self.lastBgPattern = self.ppu.bgPatternTableAddr

    def maintainSpritePatternTable(self):
        if self.lastSpritePattern != self.ppu.spritePatternTableAddr:
            self.spritePatternTable = self.ppu.dumpPtab(self.ppu.spritePatternTableAddr)
            # I can't make GL_R8UI work, so everything has to be floats
            patternTableFloats = [float(ord(x)) for x in self.spritePatternTable]
            self.cscreen.setSpritePatternTable(patternTableFloats)
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
