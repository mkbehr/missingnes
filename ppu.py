import sys

import palette
import ppucache
from rom import MirrorMode

FORCE_PPU_DEBUG = False

# Force the sprite 0 hit to occur on a given cycle. Set to None to run
# detection normally.
# (Super Mario Bros. wants a hit at frame 10322.)
FORCE_SPRITE0_CYCLE = None

SCANLINES = 262
VISIBLE_SCANLINES = 240
CYCLES_PER_SCANLINE = 341
VISIBLE_COLUMNS = 256

CYCLES_PER_FRAME = SCANLINES * CYCLES_PER_SCANLINE

VBLANK_START = 241 * CYCLES_PER_SCANLINE + 1
VBLANK_END = 261 * CYCLES_PER_SCANLINE + 1
FRAME_END = CYCLES_PER_FRAME - 1

# If a sprite 0 hit could occur at pixel (0,0), the sprite 0 flag
# would be raised at this cycle. (This isn't actually possible,
# because sprites can't be drawn on the first scanline.)
SPRITE0_CYCLE_OFFSET = 2

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

    def __init__(self, cpu, mirroring, ppu_debug = False):
        self.cpu = cpu
        self.mirroring = mirroring
        self.ppu_debug = ppu_debug or FORCE_PPU_DEBUG

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
        self.maskState = 0

        ## PPUSTATUS flags
        self.spriteOverflow = 0
        self.sprite0Hit = 0
        self.vblank = 0

        ## OAMADDR
        self.oamaddr = 0x00

        ## PPUSCROLL
        self.fineScrollX = 0
        self.fineScrollY = 0
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

        # Stored value of y scroll offset, only normally updated
        # between frames
        self.tempScrollY = 0

        self.sleepUntil(VBLANK_START, self.vblankStart)

        from screen import Screen # herp derp circular import
        self.pgscreen = Screen(self)

    def readReg(self, register):
        # Set the latch, then return it. Write-only registers just set
        # the latch, but for now they also print an error message.
        if register == REG_PPUCTRL:
            if self.ppu_debug:
                print >> sys.stderr, 'Warning: read from PPUCTRL'
        elif register == REG_PPUMASK:
            if self.ppu_debug:
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
            if self.ppu_debug:
                print >> sys.stderr, 'Warning: read from OAMADDR'
        elif register == REG_OAMDATA:
            # TODO: if (oamaddr % 4) == 3, report that bits 2-4 are 0
            # see http://wiki.nesdev.com/w/index.php/PPU_OAM
            self.latch = ord(self.oam[self.oamaddr])
        elif register == REG_PPUSCROLL:
            if self.ppu_debug:
                print >> sys.stderr, 'Warning: read from PPUSCROLL'
        elif register == REG_PPUADDR:
            if self.ppu_debug:
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
            # TODO: writing to PPUCTRL during rendering will change
            # the high scroll bits in /t/. This will change the high
            # bit for horizontal scroll on the next scanline, but the
            # high bit for vertical scroll will not be affected until
            # the next frame (unless we write to REG_PPUADDR).
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

            if self.nametableBase != oldNametableBase:
                self.maintainScroll()

            if self.ppu_debug:
                xcycle, ycycle = self.cycleToCoords(self.fineCycle())
                print "PPUCTRL (cycle %d: %d, %d): nametableBase = %d" % (
                    self.fineCycle(),
                    xcycle, ycycle,
                    self.nametableBase)

            if self.ppuMasterSlave:
                raise RuntimeError("We set the PPU master/slave bit! That's bad!")
        elif register == REG_PPUMASK:
            self.maskState = val
            grayscale = val & 0x1 # bit 0
            leftBkg = (val >> 1) & 0x1 # bit 1
            leftSprites = (val >> 2) & 0x1 # bit 2
            showBkg = (val >> 3) & 0x1 # bit 3
            showSprites = (val >> 4) & 0x1 # bit 4
            emphasizeRed = (val >> 5) & 0x1 # bit 5
            emphasizeGreen = (val >> 6) & 0x1 # bit 6
            emphasizeBlue = (val >> 7) & 0x1 # bit 7
            if self.ppu_debug and grayscale:
                print >> sys.stderr, "PPUMASK write: ignoring grayscale"
            if self.ppu_debug and (leftBkg or leftSprites):
                print >> sys.stderr, "PPUMASK write: ignoring left-column hiding"
            if self.ppu_debug and (emphasizeRed or emphasizeGreen or emphasizeBlue):
                print >> sys.stderr, "PPUMASK write: ignoring color emphasis"
        elif register == REG_PPUSTATUS:
            if self.ppu_debug:
                print >> sys.stderr, 'Warning: write to PPUSTATUS'
        elif register == REG_OAMADDR:
            self.oamaddr = val
        elif register == REG_OAMDATA:
            self.oam[self.oamaddr] = chr(val)
            self.oamaddr = (self.oamaddr + 1) % OAM_SIZE
        elif register == REG_PPUSCROLL:
            # TODO: During rendering, the first write to PPUSCROLL
            # will update the coarse x scroll in /t/, to be loaded
            # into /v/ for the next scanline. It will also change the
            # fine x scroll (horizontal position within a tile)
            # immediately.

            if self.nextScroll == 0:
                self.fineScrollX = val
                self.nextScroll = 1
                if self.ppu_debug:
                    xcycle, ycycle = self.cycleToCoords(self.fineCycle())
                    print "PPUSCROLL (cycle %d: %d, %d): x = %d" % (
                        self.fineCycle(), xcycle, ycycle, val)
            else:
                self.fineScrollY = val
                self.nextScroll = 0
                if self.ppu_debug:
                    xcycle, ycycle = self.cycleToCoords(self.fineCycle())
                    print "PPUSCROLL (cycle %d: %d, %d): y = %d" % (
                        self.fineCycle(), xcycle, ycycle, val)
                self.maintainScroll()

        elif register == REG_PPUADDR:
            # TODO: writing to PPUADDR during rendering will cause
            # strange effects, because the address register is also
            # used for the scroll position. The first write sets the
            # top 2 bits of coarse y scroll, the two nametable bits,
            # and all 3 bits of fine y scroll in /t/; however, the top
            # bit of fine y scroll is always set to 0. The second
            # write sets coarse x scroll and the bottom 3 bits of
            # coarse y scroll in /t/; then it immediately sets /v/
            # equal to /t/. This can change both horizontal and
            # vertical scrolling anywhere; it is the only way to
            # change horiz. scrolling during a scanline or vert.
            # scrolling during a frame.
            if self.nextAddr == 0:
                # addresses past $3fff are mirrored down
                self.addrHigh = val & 0x3f
                self.nextAddr = 1
            else:
                self.addrLow = val
                self.nextAddr = 0
                self.ppuaddr = self.addrLow + self.addrHigh * 0x100

                # A hack to represent PPUADDR's effect on the
                # nametable bits of the scroll coordinates. To
                # properly represent this, see big comment above.
                self.nametableBase = (self.addrHigh & 12) >> 2
                self.maintainScroll()

        elif register == REG_PPUDATA:
            self.cpu.mem.ppuWrite(self.ppuaddr, val)
            self.advanceVram()
        else:
            raise RuntimeError("PPU write to bad register %x" % register)

    def advanceVram(self):
        # TODO: advancing vram (on reads or writes to REG_PPUDATA)
        # during rendering does bizarre things to the scroll values.
        # Specifically, it increments the coarse component of X and
        # the fine component of Y (overflowing to coarse if
        # appropriate).
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
        # bit c is the same as self.bgPatternTableAddr (or spritePatternTableAddr)
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

    def tileRows(self):
        if self.mirroring == MirrorMode.horizontalMirroring:
            # horizontal mirroring means vertical scrolling
            return (VISIBLE_SCANLINES / 8) * 2
        elif self.mirroring == MirrorMode.verticalMirroring:
            return VISIBLE_SCANLINES / 8
        else:
            raise NotImplementedError("Unimplemented mirroring mode")

    def tileColumns(self):
        if self.mirroring == MirrorMode.horizontalMirroring:
            # horizontal mirroring means vertical scrolling
            return VISIBLE_COLUMNS / 8
        elif self.mirroring == MirrorMode.verticalMirroring:
            return (VISIBLE_COLUMNS / 8) * 2
        else:
            raise NotImplementedError("Unimplemented mirroring mode")

    def scrollX(self):
        coarseScrollX = (self.nametableBase % 2) * 256
        return coarseScrollX + self.fineScrollX

    def scrollY(self):
        coarseScrollY = (self.nametableBase // 2) * 240
        return coarseScrollY + self.fineScrollY

    def updateBgTiles(self):
        for tilecolumn in xrange(self.tileColumns()):
            for tilerow in xrange(self.tileRows()):
                ## BACKGROUND

                # Grab data from nametable to find pattern table
                # entry. There are 30*32 bytes in a pattern table, and
                # each byte corresponds to an 8*8-pixel tile.

                # We can pull 8 horizontally-continguous pixels at
                # once: we have a low-plane byte with the low-plane
                # bits for 8 pixels, and a high-plane byte with the
                # high-plane bits for the same 8 pixels. Finally, we
                # need to grab the background palette from the
                # attribute table.

                # This function copies over both background
                # nametables, ignoring the scroll data (both the low
                # bits from PPUSCROLL and the high bits from PPUCTRL).

                # TODO: remove assumption that there are exactly two
                # background nametables

                # Ignore the nametableBase setting from PPUCTRL here:
                # it'll become the high bits for scrolling.
                nametableBase = 0
                if (tilecolumn >= (VISIBLE_COLUMNS / 8)):
                    nametableBase += 1
                if (tilerow >= (VISIBLE_SCANLINES / 8)):
                    nametableBase += 2

                nametable = 0x2000 + 0x400 * nametableBase # TODO don't use magic numbers
                wrappedColumn = tilecolumn % (VISIBLE_COLUMNS / 8)
                wrappedRow = tilerow % (VISIBLE_SCANLINES / 8)
                nametableEntry = nametable + wrappedColumn + wrappedRow * 32
                ptabTile = ord(self.cpu.mem.ppuRead(nametableEntry))

                # TODO don't use magic numbers
                attributeRow = wrappedRow // 4
                attributeColumn = wrappedColumn // 4
                attributeTable = nametable + 0x3C0
                attributeTableEntry = attributeTable + attributeColumn + attributeRow * 8
                attributeTile = ord(self.cpu.mem.ppuRead(attributeTableEntry))

                # The attributeTile byte divides the 32x32 tile into
                # four 16x16 quarter-tiles. Bits 0-1 specify the
                # palette for the top-left quarter-tile, bits 2-3 are
                # the top-right, bits 4-5 are the bottom-left, and
                # bits 6-7 are the bottom-right.
                paletteOffset = 0
                if (wrappedColumn % 4) >= 2:
                    paletteOffset += 1*2
                if (wrappedRow % 4) >= 2:
                    paletteOffset += 2*2

                paletteNumber = (attributeTile >> paletteOffset) & 0x3

                self.pgscreen.tileIndices[tilecolumn][tilerow] = ptabTile
                self.pgscreen.paletteIndices[tilecolumn][tilerow] = paletteNumber

    def vblankStart(self):
        if self.ppu_debug:
            print "Starting vblank"
        self.draw()
        self.vblank = 1
        if self.vblankNMI:
            # signal NMI
            self.cpu.nmiPending = True
        self.sleepUntil(VBLANK_END, self.vblankEnd)

    def vblankEnd(self):
        if self.ppu_debug:
            print "Ending vblank"
        self.vblank = 0
        self.updateBgTiles()
        # It's possible that we're supposed to reset sprite 0 one
        # frame earlier, but I don't want to look up the details right
        # now
        self.sprite0Hit = 0
        self.tempScrollY = self.scrollY()
        if self.ppu_debug:
            print "Initializing frame with scroll offset (%d, %d)" % (self.scrollX(), self.scrollY())
        self.pgscreen.initFrame()
        self.sleepUntil(FRAME_END, self.frameEnd)

    def frameEnd(self):
        self.frame += 1
        self.cycle = -1
        if self.ppu_debug:
            print "BEGIN PPU FRAME %d" % self.frame
        sprite0hit = self.findSprite0Hit()
        if sprite0hit < 0:
            self.sleepUntil(VBLANK_START, self.vblankStart)
        else:
            self.sleepUntil(sprite0hit, self.flagSprite0Hit)


    def draw(self):
        # TODO: if the VRAM address points to something in
        # $3f00-$3fff, set universalBg to that instead of
        # $3f00 (though for exact behavior, this should
        # actually be checked repeatedly during the frame - I
        # don't know exactly how often). This is the
        # "background hack".
        self.universalBg = ord(self.cpu.mem.ppuRead(0x3F00)) # TODO no magic numbers

        # TODO check the frame count for off-by-one errors
        self.pgscreen.tick(self.frame)

    def flagSprite0Hit(self):
        if self.ppu_debug:
            print "Setting sprite 0 hit flag"
        self.sprite0Hit = 1
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

        # TODO skip cycle 340 on scanline 239 on odd
        # frames... hahahaha no I don't care

    def sleepUntil(self, cycle, f):
        self.nextActionCycle = cycle
        self.nextActionF = f
        self.cpu.ppuCyclesUntilAction = cycle - self.cycle
        assert (self.cpu.ppuCyclesUntilAction >= 0)

    def fineCycle(self):
        # Return the current cycle number, taking into account the
        # number of cycles tracked by the CPU.
        return self.cycle + self.cpu.ppuStoredCycles

    def cycleToCoords(self, cycle):
        return (cycle % CYCLES_PER_SCANLINE, cycle // CYCLES_PER_SCANLINE)

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


    # Find the cycle where a sprite 0 hit occurs this frame. If there
    # will not be a sprite 0 hit, return -1.
    def findSprite0Hit(self):
        if FORCE_SPRITE0_CYCLE is not None:
            return FORCE_SPRITE0_CYCLE

        # Sprite 0 hits can only happen if both background and sprites
        # are being rendered.
        if not (self.maskState & ((1 << 3) | (1 << 4))):
            if self.ppu_debug:
                print "No sprite 0 hit"
            return -1

        spritetop = ord(self.oam[0]) + 1
        # TODO account for 8x16 sprites

        if spritetop >= 0xf0:
            # Sprite 0 is wholly off the screen; no sprite 0 hit
            if self.ppu_debug:
                print "No sprite 0 hit"
            return -1

        tileIndex = ord(self.oam[1])
        attributes = ord(self.oam[2])
        spriteX = ord(self.oam[3])
        horizontalMirror = bool(attributes & 0x40)
        verticalMirror = bool(attributes & 0x80)
        # Note: palette is irrelevant for sprite 0 hits

        # fetch opacity patterns for sprite 0 and relevant bkg tiles

        # Lazily load the sprite opacity: we need to read two bytes per row
        spriteOpacity = [None for _ in xrange(8)]

        def spriteOpaque(xoffset, yoffset):
            # Load sprite opacity if necessary
            if spriteOpacity[yoffset] is None:
                lowbyte, highbyte = self.readPtab(self.spritePatternTableAddr,
                                                  yoffset, tileIndex)
                # We have two bits per pixel to represent color, but
                # the pixel is opaque if either is set. We don't care
                # which one here.
                spriteOpacity[yoffset] = lowbyte | highbyte
            # Now spriteOpacity[yoffset] is a byte whose bits
            # represent pixel opacity: the most-significant bit
            # represents the leftmost pixel in the row.
            return bool(spriteOpacity[yoffset] & (0x80 >> xoffset))

        # Same for background opacity, except that we potentially have
        # four background tiles to read. This list is indexed first by
        # horizontal tile (0 or 1) and then by vertical row.
        bkgOpacity = [[None for _ in xrange(8*2)] for _ in xrange(2)]
        bkgTopTile = spritetop // 8
        bkgLeftTile = spriteX // 8
        bkgTopPixel = bkgTopTile * 8
        bkgLeftPixel = bkgLeftTile * 8

        def bkgOpaque(x, y):
            xoffset = x - bkgLeftPixel
            yoffset = y - bkgTopPixel
            if xoffset < 8:
                tileColumnOffset = 0
            else:
                tileColumnOffset = 1

            if bkgOpacity[tileColumnOffset][yoffset] is None:
                tileColumn = bkgLeftTile + tileColumnOffset
                if yoffset < 8:
                    tileRow = bkgTopTile
                else:
                    tileRow = bkgTopTile + 1

                nametable = 0x2000 + 0x400 * self.nametableBase # TODO don't use magic numbers
                nametableEntry = nametable + tileColumn + tileRow * 32
                # We could cache this read, but it probably doesn't matter much.
                bkgTile = ord(self.cpu.mem.ppuRead(nametableEntry))

                lowbyte, highbyte = self.readPtab(self.bgPatternTableAddr,
                                                  yoffset % 8, bkgTile)
                bkgOpacity[tileColumnOffset][yoffset] = lowbyte | highbyte
            return bool(bkgOpacity[tileColumnOffset][yoffset]
                        & (0x80 >> (xoffset % 8)))

        # TODO account for 8x16 sprites
        for xoffset in xrange(8):
            x = xoffset + spriteX
            for yoffset in xrange(8):
                y = yoffset + spritetop
                if (spriteOpaque(xoffset,yoffset) and
                    bkgOpaque(x,y)):
                    out = (x
                           + (y * CYCLES_PER_SCANLINE)
                           + SPRITE0_CYCLE_OFFSET)
                    if self.ppu_debug:
                        print ("Sprite 0 hit at (%d,%d): PPU cycle %d" %
                               (x, y, out))
                    return out

        # Didn't find a hit.
        if self.ppu_debug:
            print "No sprite 0 hit"
        return -1

    def maintainScroll(self):
        """Maintains scroll coordinates during rendering by pushing a scroll
region to the screen module. Does nothing outside of rendering. Can
safely be called multiple times during the same render frame.

        """

        # Handle scroll updates during rendering. This is not
        # completely accurate, but it'll work for simple cases. (For
        # one thing, we should write on a write to the x scroll, not
        # the y scroll. For another, writes to the x scroll should
        # modify the low 3 bits immediately but the upper bits at the
        # end of the line. (But in practice, that last one isn't easy
        # to control for game-writers.))

        (xStart, yTop) = self.cycleToCoords(self.fineCycle())
        if xStart > 0:
            yTop += 1
            xStart = 0
        # Check yTop instead of vblank, because we go off the
        # screen a bit before the vblank flag is actually set.
        if yTop < VISIBLE_SCANLINES:
            self.pgscreen.recordScroll(self.scrollX(), self.tempScrollY,
                                       xStart, yTop)




    def printTile(self, base, tile):

        """Print a representation of a tile to stdout. For debug purposes."""
        import sys
        for finey in xrange(8):
            (lowbyte, highbyte) = self.readPtab(base, finey, tile)
            for finex in xrange(8):
                pattern = 0
                if (lowbyte & (1 << (7-finex))):
                    pattern += 1
                if (highbyte & (1 << (7-finex))):
                    pattern += 2
                if pattern:
                    sys.stdout.write(str(pattern))
                else:
                    sys.stdout.write(".")
            sys.stdout.write("\n")
