"""Handle drawing objects to the screen. The code is seperate from
ppu.py because this doesn't handle the PPU's internal state - the view
to ppu.py's controller, let's say. (or is that the model? should we
have more separation?)

"""

import pyglet
from pyglet.window import key

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

        self.window = pyglet.window.Window(width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
        self.window.on_draw = self.on_draw

        self.keys = key.KeyStateHandler()
        self.window.push_handlers(self.keys)

        dummyImage = pyglet.image.ImageData(1, 1, 'RGBA', "\x00\x00\x00\x00", pitch= 4)

        self.bgBatch = pyglet.graphics.Batch()
        self.bgSprites = [
            [pyglet.sprite.Sprite(dummyImage, x*8, SCREEN_HEIGHT - y*8 - 8, batch=self.bgBatch)
             for y in range(TILE_ROWS)]
            for x in range(TILE_COLUMNS)]

        self.spriteBatch = pyglet.graphics.Batch()
        self.spriteSprites = [pyglet.sprite.Sprite(dummyImage, 0, 0, batch=self.spriteBatch)
                              for sprite_i in range(ppu.OAM_SIZE / ppu.OAM_ENTRY_SIZE)]

    def tick(self, frame): # TODO consider turning this into a more general callback that the ppu gets
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
        (bg_r, bg_g, bg_b) = palette.PALETTE[self.ppu.universalBg]
        pyglet.gl.glClearColor(bg_r, bg_g, bg_b, 255)
        self.window.clear()
        self.bgBatch.draw()
        self.spriteBatch.draw()
