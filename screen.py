"""Handle drawing objects to the screen. The code is seperate from
ppu.py because this doesn't handle the PPU's internal state - the view
to ppu.py's controller, let's say. (or is that the model? should we
have more separation?)

"""

import pyglet

from PIL import Image
import numpy as np

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

    def __init__(self, ppu):

        self.ppu = ppu
        
        self.window = pyglet.window.Window(width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
        self.window.on_draw = self.on_draw

    def tick(self):
        pyglet.clock.tick()

        for window in pyglet.app.windows:
            window.switch_to()
            window.dispatch_events()
            window.dispatch_event('on_draw')
            window.flip()

    def on_draw(self):
        # Background: draw each background tile.

        # There are ppu.VISIBLE_SCANLINES/8 rows of tiles and
        # ppu.VISIBLE_COLUMNS/8 columns. Each tile is 8*8 pixels.

        # Actually, let's start by just drawing the thing to screen
        # like we do now. Then we can speed it up.

        # a bit hacky, but this works for now
        nparray = np.array(self.ppu.screen, dtype='float').T
        nparray /= 3.0
        npint = np.uint8(nparray * 255)

        raw_img = npint.tobytes()

        pglimage = pyglet.image.ImageData(SCREEN_WIDTH, SCREEN_HEIGHT, 'L',
                                          raw_img, pitch= -SCREEN_WIDTH)
        self.window.clear()
        pglimage.blit(0,0)

        # Sprites: TODO
        pass
