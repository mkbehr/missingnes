import sys
import numpy as np

import palette
import ppucache
import sprite

from OpenGL.GL import * # TODO this file does not want GL code

DRAW_GRID = False

PPU_DEBUG = False

SCANLINES = 262
VISIBLE_SCANLINES = 240
CYCLES_PER_SCANLINE = 341
VISIBLE_COLUMNS = 256

CYCLES_PER_FRAME = SCANLINES * CYCLES_PER_SCANLINE

VBLANK_START = 241 * CYCLES_PER_SCANLINE + 1
VBLANK_END = 261 * CYCLES_PER_SCANLINE + 1
DRAW_CYCLE = CYCLES_PER_FRAME - 1

REG_PPUCTRL = 0
REG_PPUMASK = 1
REG_PPUSTATUS = 2
REG_OAMADDR = 3
REG_OAMDATA = 4
REG_PPUSCROLL = 5
REG_PPUADDR = 6
REG_PPUDATA = 7

# TODO consider whether OAM and palette memory should be stored here
# instead of in the memory object
OAM_SIZE = 256
OAM_ENTRY_SIZE = 4
PALETTE_SIZE = 32

MAX_SPRITES = 8 # maximum number of sprites displayed per scanline

BG_PALETTE_BASE = 0x3f00
SPRITE_PALETTE_BASE = 0x3f10

class PPU(object):

    def __init__(self, cpu):
        self.cpu = cpu

        self.cache = ppucache.PPUCache(self)

        self.scanline = 261
        self.cycle = 0
        self.frame = 0

        # values in the latch decay over time in the actual NES, but I
        # don't think that's worth emulating
        self.latch = 0x0

        self.oam = ['\x00' for i in range(OAM_SIZE)]
        self.paletteRam = ['\x00' for i in range(PALETTE_SIZE)]

        ## PPUCTRL flags

        # base nametable address: 0 = $2000; 1 = $2400; 2 = $2800; 3 = $2C00
        self.nametableBase = 0
        # VRAM address increment per CPU read/write of PPUDATA.
        # 0: add 1, going across; 1: add 32, going down
        self.vramInc = 0
        # Sprite pattern table address for 8x8 sprites.
        # 0: $0000; 1: $1000; ignored in 8x16 mode
        self.spritePatternTableAddr = 0
        # Background pattern table address. 0: $0000; 1: $1000
        self.bgPatternTableAddr = 0
        # Sprite size. 0: 8x8; 1: 8x16.
        self.spriteSize = 0
        # PPU master/slave select. Setting to 1 can damage an
        # unmodified NES, so we'll just throw an error if someone
        # tries to set it.
        self.ppuMasterSlave = 0
        # Whether to generate an NMI at the start of the vertical
        # blanking interval.
        self.vblankNMI = 0

        ## PPUMASK flags
        self.grayscale = 0
        self.leftBkg = 0
        self.leftSprites = 0
        self.showBkg = 0
        self.showSprites = 0
        self.emphasizeRed = 0
        self.emphasizeGreen = 0
        self.emphasizeBlue = 0

        ## PPUSTATUS flags
        self.spriteOverflow = 0
        self.sprite0Hit = 0
        self.vblank = 0

        ## OAMADDR
        self.oamaddr = 0x00

        ## PPUSCROLL
        self.scrollX = 0
        self.scrollY = 0
        self.nextScroll = 0 # 0 for X, 1 for Y

        ## PPUADDR
        self.ppuaddr = 0
        self.addrHigh = 0
        self.addrLow = 0
        self.nextAddr = 0 # 0 for high, 1 for low

        ## PPUDATA
        self.ppuDataBuffer = 0

        ## Sprite-relevant state
        self.spritesThisScanline = [None for i in range(MAX_SPRITES)]
        self.nSpritesThisScanline = 0

        ## Background tile caches
        self.bglowbyte = 0
        self.bghighbyte = 0
        self.bgpalette = [0,0,0] # global palette indexes for numbers 1, 2, and 3
        self.universalBg = 0 # global palette index for number 0

        # Whether or not to redraw a background tile. This will get
        # messier once sprites exist; for now pretend they don't.
        self.redrawtile = np.invert( # pypy doesn't like np.ones
            np.zeros((VISIBLE_COLUMNS/8, VISIBLE_SCANLINES/8),
                     dtype='bool'))
        # The same thing but for next frame. (We want to fiddle with
        # this before we're done drawing a given tile)
        self.nextredrawtile = np.invert(
                    np.zeros((VISIBLE_COLUMNS/8, VISIBLE_SCANLINES/8),
                             dtype='bool'))

        self.screenarray = np.zeros((VISIBLE_COLUMNS, VISIBLE_SCANLINES), dtype='uint8')
        # for sprite 0
        self.bkgOpacity = np.zeros((VISIBLE_COLUMNS, VISIBLE_SCANLINES), dtype='bool')

        self.sleepUntil(VBLANK_START, self.vblankStart)

        from screen import Screen # herp derp circular import
        self.pgscreen = Screen(self)

    def readReg(self, register):
        # Set the latch, then return it. Write-only registers just set
        # the latch, but for now they also print an error message.
        if register == REG_PPUCTRL:
            if PPU_DEBUG:
                print >> sys.stderr, 'Warning: read from PPUCTRL'
        elif register == REG_PPUMASK:
            if PPU_DEBUG:
                print >> sys.stderr, 'Warning: read from PPUMASK'
        elif register == REG_PPUSTATUS:
            # keep first five bits of latch
            self.latch &= 0x1f
            if self.spriteOverflow:
                self.latch |= 0x20
            if self.sprite0Hit:
                self.latch |= 0x40
            if self.vblank:
                self.latch |= 0x80
            # TODO there's some weirdness with reading this register
            # within like a cycle of when vblank begins, but I don't
            # think I care enough to emulate that
            self.vblank = False
            # clear address latch (pretending they're two different things)
            self.nextScroll = 0
            self.nextAddr = 0
        elif register == REG_OAMADDR:
            if PPU_DEBUG:
                print >> sys.stderr, 'Warning: read from OAMADDR'
        elif register == REG_OAMDATA:
            # TODO: if (oamaddr % 4) == 3, report that bits 2-4 are 0
            # see http://wiki.nesdev.com/w/index.php/PPU_OAM
            self.latch = ord(self.oam[self.oamaddr])
        elif register == REG_PPUSCROLL:
            if PPU_DEBUG:
                print >> sys.stderr, 'Warning: read from PPUSCROLL'
        elif register == REG_PPUADDR:
            if PPU_DEBUG:
                print >> sys.stderr, 'Warning: read from PPUADDR'
        elif register == REG_PPUDATA:
            # do not question the PPUDATA post-fetch read buffer
            if self.ppuaddr < 0x3f00:
                self.latch = self.ppuDataBuffer
                self.ppuDataBuffer = ord(self.cpu.mem.ppuRead(self.ppuaddr))
            else:
                self.ppuDataBuffer = ord(self.cpu.mem.ppuRead(self.ppuaddr))
                self.latch = self.ppuDataBuffer
            self.advanceVram()
        else:
            raise RuntimeError("PPU read from bad register %x" % register)
        return chr(self.latch)

    def writeReg(self, register, val):
        if isinstance(val, str): # someday we will want to get rid of this chr/ord weirdness
            val = ord(val)
        self.latch = val
        if register == REG_PPUCTRL:
            oldNametableBase = self.nametableBase
            oldBgPatternTableAddr = self.bgPatternTableAddr

            self.nametableBase = val & 0x3 # bits 0,1
            self.vramInc = (val >> 2) & 0x1 # bit 2
            self.spritePatternTableAddr = (val >> 3) & 0x1 # bit 3
            self.bgPatternTableAddr = (val >> 4) & 0x1 # bit 4
            self.spriteSize = (val >> 5) & 0x1 # bit 5
            self.ppuMasterSlave = (val >> 6) & 0x1 # bit 6
            self.vblankNMI = (val >> 7) & 0x1 # bit 7
            # TODO if we just set vblankNMI and we're in vblank, this
            # might be supposed to trigger the NMI

            if (self.nametableBase != oldNametableBase or
                self.bgPatternTableAddr != oldBgPatternTableAddr):
                self.flushBgCache()

            if self.ppuMasterSlave:
                raise RuntimeError("We set the PPU master/slave bit! That's bad!")
        elif register == REG_PPUMASK:
            self.grayscale = val & 0x1 # bit 0
            self.leftBkg = (val >> 1) & 0x1 # bit 1
            self.leftSprites = (val >> 2) & 0x1 # bit 2
            self.showBkg = (val >> 3) & 0x1 # bit 3
            self.showSprites = (val >> 4) & 0x1 # bit 4
            self.emphasizeRed = (val >> 5) & 0x1 # bit 5
            self.emphasizeGreen = (val >> 6) & 0x1 # bit 6
            self.emphasizeBlue = (val >> 7) & 0x1 # bit 7
            if PPU_DEBUG and (self.emphasizeRed or self.emphasizeGreen or self.emphasizeBlue):
                print >> sys.stderr, "PPUMASK write: ignoring color emphasis"
            pass
        elif register == REG_PPUSTATUS:
            if PPU_DEBUG:
                print >> sys.stderr, 'Warning: write to PPUSTATUS'
        elif register == REG_OAMADDR:
            self.oamaddr = val
        elif register == REG_OAMDATA:
            self.oam[self.oamaddr] = chr(val)
            self.oamaddr = (self.oamaddr + 1) % OAM_SIZE
        elif register == REG_PPUSCROLL:
            # TODO once scrolling exists, this may affect cache
            if self.nextScroll == 0:
                self.scrollX = val
                self.nextScroll = 1
            else:
                self.scrollY = val
                self.nextScroll = 0
        elif register == REG_PPUADDR:
            if self.nextAddr == 0:
                # addresses past $3fff are mirrored down
                self.addrHigh = val & 0x3f
                self.nextAddr = 1
            else:
                self.addrLow = val
                self.nextAddr = 0
                self.ppuaddr = self.addrLow + self.addrHigh * 0x100
        elif register == REG_PPUDATA:
            self.cpu.mem.ppuWrite(self.ppuaddr, val)
            self.advanceVram()
        else:
            raise RuntimeError("PPU write to bad register %x" % register)

    def advanceVram(self):
        if self.vramInc == 0:
            self.ppuaddr += 1
        else:
            self.ppuaddr += 32
        self.ppuaddr &= 0xffff

    def readPtab(self, base, finey, tile):
        """Read an entry from a pattern table.
        Arguments:
        - base: 0 or 1 corresponding to the pattern table base
        - finey: Fine y offset. y position within the tile (0-7).
        - tile: One byte determining the tile within the table."""
        # finding pattern table entry:
        #
        # bits 0 through 2 are the "fine y offset", the y position
        # within a tile (y position % 8, I guess)
        #
        # bit 3 is the bitplane: we'll need to read once with it
        # set and once with it unset to get two bits of color
        #
        # bits 4 through 7 are the column of the tile (column / 8)
        #
        # bits 8 through b are the tile row (row / 8)
        #
        # bit c is the same as self.bgPatternTableAddr
        #
        # bits d through f are 0 (pattern tables go from 0000 to 1fff)

        lowplane = (
            (finey) + # 0-2: fine y offset
            (0 << 3) + # 3: dataplane
            (tile << 4) + # 4-11: column and row
            (base << 12)) # 12: pattern table base
        # bits d through f are 0 (pattern tables go from 0000 to 1fff)
        assert ((lowplane & 8) == 0)
        highplane = lowplane | 8 # set bit 3 for high dataplane

        lowbyte = ord(self.cpu.mem.ppuRead(lowplane))
        highbyte = ord(self.cpu.mem.ppuRead(highplane))

        return (lowbyte,highbyte)

    def updateBgTiles(self):
        for tilecolumn in range(VISIBLE_COLUMNS/8):
            for tilerow in range(VISIBLE_SCANLINES/8):
                ## BACKGROUND

                # Grab data from nametable to find pattern table
                # entry. There are 30*32 bytes in a pattern table, and
                # each byte corresponds to an 8*8-pixel tile.

                # If we're at the start of a tile, refresh our cache. We
                # can pull 8 horizontally-continguous pixels at once; we
                # have a low-plane byte with the low-plane bits for 8
                # pixels, and a high-plane byte with the high-plane bits
                # for the same 8 pixels. Finally, we need to grab the
                # background palette from the attribute table.

                nametable = 0x2000 + 0x400 * self.nametableBase # TODO don't use magic numbers
                # double-check this:
                nametableEntry = nametable + tilecolumn + tilerow * 32
                ptabTile = ord(self.cpu.mem.ppuRead(nametableEntry))

                # TODO don't use magic numbers
                attributeRow = tilerow / 4 # rely on truncating down here
                attributeColumn = tilecolumn / 4
                attributeTable = nametable + 0x3C0
                attributeTableEntry = attributeTable + attributeColumn + attributeRow * 8
                attributeTile = ord(self.cpu.mem.ppuRead(attributeTableEntry))

                # The attributeTile byte divides the 32x32 tile into
                # four 16x16 quarter-tiles. Bits 0-1 specify the
                # palette for the top-left quarter-tile, bits 2-3 are
                # the top-right, bits 4-5 are the bottom-left, and
                # bits 6-7 are the bottom-right.
                paletteOffset = 0
                if (tilecolumn % 4) >= 2:
                    paletteOffset += 1*2
                if (tilerow % 4) >= 2:
                    paletteOffset += 2*2

                paletteNumber = (attributeTile >> paletteOffset) & 0x3

                self.pgscreen.tileIndices[tilecolumn][tilerow] = ptabTile
                self.pgscreen.paletteIndices[tilecolumn][tilerow] = paletteNumber

    def updateSprites(self):
        # TODO maybe this should just be done at vblank_end? Also should probably process background here too?
        for sprite_i in range(OAM_SIZE / OAM_ENTRY_SIZE):
            sprite_oam_base = sprite_i * OAM_ENTRY_SIZE
            # The first byte of a sprite's entry is one less than
            # its y-coordinate. (This does mean that sprites can
            # never be drawn on scanline 0.)
            spritetop = ord(self.oam[sprite_oam_base]) + 1
            # TODO account for 8x16 sprites

            # BEGIN caching code

            # Ignoring things like sprite-per-scanline limits,
            # just run the caching code on every sprite. (However,
            # OAM is not read-only like sprites, so we'll need to
            # process more of it here.)

            tileIndex = ord(self.oam[sprite_oam_base+1])
            attributes = ord(self.oam[sprite_oam_base+2])
            spriteX = ord(self.oam[sprite_oam_base+3])
            spritePalette = attributes & 0x3
            horizontalMirror = bool(attributes & 0x40)
            verticalMirror = bool(attributes & 0x80)

            # TODO no magic numbers
            paletteAddr = 0x3F11 + (spritePalette * 4)
            paletteData = [ord(self.cpu.mem.ppuRead(paletteAddr)),
                           ord(self.cpu.mem.ppuRead(paletteAddr+1)),
                           ord(self.cpu.mem.ppuRead(paletteAddr+2))]

            spriteTex = self.cache.spriteTexture(
                base = self.spritePatternTableAddr,
                tile = tileIndex,
                flipH = horizontalMirror,
                flipV = verticalMirror,
                paletteData = paletteData)
            # TODO assign texture to tile

            # self.pgscreen.spriteSprites[sprite_i]._set_texture(spriteTex)
            # self.pgscreen.spriteSprites[sprite_i].x = spriteX
            # self.pgscreen.spriteSprites[sprite_i].y = (VISIBLE_SCANLINES) - spritetop - 8
            # END caching code

            # TODO emulate sprite overflow, including batshit behavior documented
            # here:
            # http://wiki.nesdev.com/w/index.php/PPU_sprite_evaluation

    def vblankStart(self):
        self.vblank = 1
        if self.vblankNMI:
            # signal NMI
            self.cpu.nmiPending = True
        self.sleepUntil(VBLANK_END, self.vblankEnd)

    def vblankEnd(self):
        self.vblank = 0
        self.updateSprites()
        self.updateBgTiles()
        # It's possible that we're supposed to reset sprite 0 one
        # frame earlier, but I don't want to look up the details right
        # now
        self.sprite0Hit = 0
        self.sleepUntil(DRAW_CYCLE, self.drawCycle)

    def drawCycle(self):
        self.frame += 1
        self.cycle = -1
        # TODO: if the VRAM address points to something in
        # $3f00-$3fff, set universalBg to that instead of
        # $3f00 (though for exact behavior, this should
        # actually be checked repeatedly during the frame - I
        # don't know exactly how often). This is the
        # "background hack".
        self.universalBg = ord(self.cpu.mem.ppuRead(0x3F00)) # TODO no magic numbers
        if PPU_DEBUG:
            print "BEGIN PPU FRAME %d" % self.frame
        # TODO check the frame count for off-by-one errors
        self.pgscreen.tick(self.frame)
        self.sleepUntil(VBLANK_START, self.vblankStart)

    def ppuTick(self, ticks):
        # streamline calls to this as follows:
        #
        # - only do anything on certain ticks (if we can track where
        #   sprites are, we can avoid redrawing most of the screen)
        # - keep track of when we next have to do things
        # - don't call ppuTick until then (but act gracefully if that does happen)

        if self.cycle + ticks >= self.nextActionCycle:
            nextTicks = self.cycle + ticks - self.nextActionCycle
            # set this now, because calling the next action will change nextActionCycle
            self.cycle = self.nextActionCycle % CYCLES_PER_FRAME
            self.nextActionF()
            assert (self.cycle < self.nextActionCycle)
            if nextTicks > 0:
                self.ppuTick(nextTicks)
        else:
            self.cycle = (self.cycle + ticks) % CYCLES_PER_FRAME

        # TODO check for sprite 0 hits somewhere
        # if False:
        #     self.sprite0hit = 1

        # TODO skip cycle 340 on scanline 239 on odd
        # frames... hahahaha no I don't care

    def sleepUntil(self, cycle, f):
        self.nextActionCycle = cycle
        self.nextActionF = f
        self.cpu.ppuCyclesUntilAction = cycle - self.cycle
        assert (self.cpu.ppuCyclesUntilAction >= 0)

    def flushBgCache(self):
        # Clear our background tile cache: we'll redraw the whole
        # background next frame. Currently this does nothing.
        pass

    def flushBgTile(self, tileX, tileY):
        # Currently this does nothing.

        # Clear our background tile cache for a single tile. This
        # should be called when we write to the PPU nametable address
        # corresponding to our active nametable. For now I'm going to
        # have the memory management code deal with that - that's
        # going to involve some weird interplay between the two
        # modules, so I might want to reorganize that eventually.

        # first make sure we're not actually writing to the attribute table
        if tileY < VISIBLE_SCANLINES / 8:
            pass
        else:
            # if we are, just flush everything to be safe
            self.flushBgCache()
            pass

    def dumpPtab(self, base):
        """Returns a string of bytes representing the specified half of the pattern table. The bytes are stored in a large atlas texture of dimension 8*256 by 8."""
        # this might be a bit slow for now, but it shouldn't be called
        # much, at least for early games. If I want to figure out the
        # details, it should be possible to directly dump the memory
        # into the string, maybe given some sort of transformation.
        out = bytearray(256*8*8)
        for tile in xrange(256):
            for y in xrange(8):
                (lowbyte, highbyte) = self.readPtab(base, y, tile)
                for x in xrange(8):
                    lowbit = (lowbyte >> (7-x)) & 1
                    highbit = (highbyte >> (7-x)) & 1
                    pixel = lowbit + 2 * highbit
                    out[x + 8*256*y + 8*tile] = pixel
        return str(out)

    def dumpLocalPalettes(self, base):
        """Returns a list of floats representing the local palette starting at the base."""
        out = [0.0 for i in range(16*4)]
        for i in range(16):
            if (i % 4) == 0:
                continue
            paletteIndex = ord(self.cpu.mem.ppuRead(base + i))
            out[4*i:(4*i)+3] = [float(x)/255.0 for x in palette.palette(paletteIndex)] # rgb
            out[(4*i)+3] = 1.0 # alpha
        return out
