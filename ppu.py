import sys
import numpy as np

PPU_DEBUG = True

SCANLINES = 262
VISIBLE_SCANLINES = 240
CYCLES = 341
VISIBLE_COLUMNS = 256

VBLANK_START = (241,1)
VBLANK_END = (261,1)

REG_PPUCTRL = 0
REG_PPUMASK = 1
REG_PPUSTATUS = 2
REG_OAMADDR = 3
REG_OAMDATA = 4
REG_PPUSCROLL = 5
REG_PPUADDR = 6
REG_PPUDATA = 7

OAM_SIZE = 256

class PPU(object):

    def __init__(self, cpu):
        self.cpu = cpu

        self.scanline = 261
        self.cycle = 0
        self.frame = 0

        # values in the latch decay over time in the actual NES, but I
        # don't think that's worth emulating
        self.latch = 0x0

        self.oam = ['\x00' for i in range(OAM_SIZE)]

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

        ## TODO PPUMASK flags

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

        ## Background tile caches
        self.bglowbyte = 0
        self.bghighbyte = 0

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
            self.latch = ord(self.oam[self.oamaddr])
        elif register == REG_PPUSCROLL:
            if PPU_DEBUG:
                print >> sys.stderr, 'Warning: read from PPUSCROLL'
        elif register == REG_PPUADDR:
            if PPU_DEBUG:
                print >> sys.stderr, 'Warning: read from PPUADDR'
        elif register == REG_PPUDATA:
            self.latch = ord(self.cpu.mem.ppuRead(self.ppuaddr))
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
            if PPU_DEBUG:
                print >> sys.stderr, "Ignoring write to PPUMASK for now: {0:08b}".format(val)
                print >> sys.stderr, "PPUMASK write: next instruction is %x" % self.cpu.PC
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
                self.addrHigh = val
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

    def ppuTick(self):
        # TODO streamline calls to this as follows:
        # - only do anything on certain ticks (if we can track where
        #   sprites are, we can avoid redrawing most of the screen)
        # - keep track of when we next have to do things
        # - don't call ppuTick until then
        
        if (self.scanline, self.cycle) == VBLANK_START:
            self.vblank = 1
            if self.vblankNMI:
                # signal NMI
                self.cpu.nmiPending = True
        elif (self.scanline, self.cycle) == VBLANK_END:
            self.vblank = 0

        # if we're on a visible pixel, draw that pixel, unless we're
        # not redrawing it
        if (self.scanline < VISIBLE_SCANLINES and self.cycle < VISIBLE_COLUMNS
            and self.redrawtile[self.cycle/8, self.scanline/8]):
            # Grab data from nametable to find pattern table
            # entry. There are 30*32 bytes in a pattern table, and
            # each byte corresponds to an 8*8-pixel tile. So I guess
            # those bytes are going to correspond to bits 4 through b
            # of the pattern table address? (make sure they're in the
            # right order) So:

            row = self.scanline
            column = self.cycle

            tilerow = row / 8
            tilecolumn = column / 8

            # If we're at the start of a tile, refresh our cache. We
            # can pull 8 horizontally-continguous pixels at once; we
            # have a low-plane byte with the low-plane bits for 8
            # pixels, and a high-plane byte with the high-plane bits
            # for the same 8 pixels.
            if (column % 8) == 0:

                nametable = 0x2000 + 0x400 * self.nametableBase # TODO don't use magic numbers
                # double-check this:
                ptabAddr = nametable + tilecolumn + tilerow * 32
                ptabEntry = ord(self.cpu.mem.ppuRead(ptabAddr))
                # and now ptabEntry is (probably) bits 4 through b of the
                # pattern table address, at which point we just need to
                # set bits 0-3 and c as described below

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
                    (row % 8) + # 0-2: fine y offset
                    (0 << 3) + # 3: dataplane
                    (ptabEntry << 4) + # 4-11: column and row (double-check)
                    (self.bgPatternTableAddr << 12)) # 12: pattern table base
                highplane = lowplane | 8 # set bit 3 for high dataplane

                self.bglowbyte = ord(self.cpu.mem.ppuRead(lowplane))
                self.bghighbyte = ord(self.cpu.mem.ppuRead(highplane))

            finex = column % 8
            # most significant bit is leftmost bit
            finexbit = 7 - finex
            
            pixelbit0 = (self.bglowbyte >> finexbit) & 0x1
            pixelbit1 = (self.bghighbyte >> finexbit) & 0x1
            colorindex = pixelbit0 + pixelbit1 * 2
            # start by just interpreting colorindex as a grayscale
            # value from 0 (black) to 3 (white); eventually we will
            # want to look up a color from the attribute tables
            
            # color = TODOrelevantgray(colorindex)
            # TODOdrawpixel(TODOrow, TODOcolumn, TODOcolor)
            color = colorindex * 85 # convert to 0-255 grayscale for now

            self.screenarray[column,row] = color
            
        self.cycle = (self.cycle + 1) % CYCLES
        if self.cycle == 0:
            self.scanline = (self.scanline + 1) % SCANLINES
            if self.scanline == 0:
                self.frame += 1
                # update our tiles to redraw: note that it's important
                # that this happens here, right at the end of vblank,
                # so that changes during vblank will be reflected
                self.redrawtile = self.nextredrawtile
                # now, cache everything unless we know otherwise
                self.nextredrawtile = np.zeros((VISIBLE_COLUMNS/8,
                                                VISIBLE_SCANLINES/8),
                                               dtype='bool')
                if PPU_DEBUG:
                    print "BEGIN PPU FRAME %d" % self.frame
                self.pgscreen.tick()
        # TODO skip cycle 340 on scanline 239 on odd
        # frames... hahahaha no I don't care

    def flushBgCache(self):
        # Clear our background tile cache: we'll redraw the whole
        # background next frame.
        self.nextredrawtile = np.invert(
            np.zeros((VISIBLE_COLUMNS/8, VISIBLE_SCANLINES/8),
                     dtype='bool'))

    def flushBgTile(self, tileX, tileY):
        # Clear our background tile cache for a single tile. This
        # should be called when we write to the PPU nametable address
        # corresponding to our active nametable. For now I'm going to
        # have the memory management code deal with that - that's
        # going to involve some weird interplay between the two
        # modules, so I might want to reorganize that eventually.

        # first make sure we're not actually writing to the attribute table
        if tileY < VISIBLE_SCANLINES / 8:
            self.nextredrawtile[tileX, tileY] = True
        else:
            # if we are, just flush everything to be safe
            self.flushBgCache()
            pass
