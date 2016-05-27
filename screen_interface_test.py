from ctypes import CDLL, c_void_p, c_int, c_float
import time

from screen import LOCAL_PALETTES_LENGTH

libscreen = CDLL("libscreen.so")
libscreen.ex_constructScreen.restype = c_void_p

libscreen.ex_setUniversalBg.argtypes = [c_void_p, c_int]

libscreen.ex_setLocalPalettes.argtypes = [c_void_p, (c_float * LOCAL_PALETTES_LENGTH)]

libscreen.ex_drawToBuffer.argtypes = [c_void_p]

libscreen.ex_draw.argtypes = [c_void_p]
libscreen.ex_draw.restype = c_int

drawval = 0
bg = 0

palettes = [0.0 for i in xrange(LOCAL_PALETTES_LENGTH)]
c_paletteInput = (c_float * LOCAL_PALETTES_LENGTH) (*palettes)

screen = libscreen.ex_constructScreen()

while drawval == 0:
    libscreen.ex_setUniversalBg(screen, bg)
    bg = (bg + 1) % 0x40
    libscreen.ex_setLocalPalettes(screen, c_paletteInput)
    libscreen.ex_drawToBuffer(screen)
    drawval = libscreen.ex_draw(screen)
    time.sleep(0.2)

print "done"
