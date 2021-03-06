# Current palette taken from the bottom of this page:
# http://wiki.nesdev.com/w/index.php/PPU_palettes

import numpy as np

PALETTE = np.array([
    #             0                 1                 2                 3
    ( 84,  84,  84),  (  0,  30, 116),  (  8,  16, 144),  ( 48,   0, 136), # $00
    ( 68,   0, 100),  ( 92,   0,  48),  ( 84,   4,   0),  ( 60,  24,   0), # $04
    ( 32,  42,   0),  (  8,  58,   0),  (  0,  64,   0),  (  0,  60,   0), # $08
    (  0,  50,  60),  (  0,   0,   0),  (  0,   0,   0),  (  0,   0,   0), # $0c
    (152, 150, 152),  (  8,  76, 196),  ( 48,  50, 236),  ( 92,  30, 228), # $10
    (136,  20, 176),  (160,  20, 100),  (152,  34,  32),  (120,  60,   0), # $14
    ( 84,  90,   0),  ( 40, 114,   0),  (  8, 124,   0),  (  0, 118,  40), # $18
    (  0, 102, 120),  (  0,   0,   0),  (  0,   0,   0),  (  0,   0,   0), # $1c
    (236, 238, 236),  ( 76, 154, 236),  (120, 124, 236),  (176,  98, 236), # $20
    (228,  84, 236),  (236,  88, 180),  (236, 106, 100),  (212, 136,  32), # $24
    (160, 170,   0),  (116, 196,   0),  ( 76, 208,  32),  ( 56, 204, 108), # $28
    ( 56, 180, 204),  ( 60,  60,  60),  (  0,   0,   0),  (  0,   0,   0), # $2c
    (236, 238, 236),  (168, 204, 236),  (188, 188, 236),  (212, 178, 236), # $30
    (236, 174, 236),  (236, 174, 212),  (236, 180, 176),  (228, 196, 144), # $34
    (204, 210, 120),  (180, 222, 120),  (168, 226, 144),  (152, 226, 180), # $38
    (160, 214, 228),  (160, 162, 160),  (  0,   0,   0),  (  0,   0,   0)  # $3c
], dtype='uint8')

# PALETTE_BYTES = PALETTE[:].tobytes()

# # some ugly code here as I figure out the best format to have this in
# RGBA_PALETTE_BYTEENTRIES = []
# for (r,g,b) in PALETTE:
#     RGBA_PALETTE_BYTEENTRIES.append(chr(r) + chr(g) + chr(b) + chr(255))

def palette(index):
    return PALETTE[index,:]

# def smallPaletteBytes(bg, paletteData):
#     # excessively long but I don't want to look up library functions
#     return PALETTE[[bg, paletteData[0], paletteData[1], paletteData[2]],:].tobytes()
