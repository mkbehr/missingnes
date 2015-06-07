import sys

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
        self.frameparity = 0 # skip the last cycle of scanline 261 on odd frames (TODO)

        # values in the latch decay over time in the actual NES, but I
        # don't think that's worth emulating
        self.latch = 0x0

        self.oam = '\x00' * OAM_SIZE

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
        

    def readReg(self, register):
        # Set the latch, then return it. Write-only registers just set
        # the latch, but for now they also print an error message.
        if register == REG_PPUCTRL:
            print >> sys.stderr, 'Warning: read from PPUCTRL'
        elif register == REG_PPUMASK:
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
            # TODO clear address latch
            self.nextScroll = 0
        elif register == REG_OAMADDR:
            print >> sys.stderr, 'Warning: read from OAMADDR'
        elif register == REG_OAMDATA:
            raise NotImplementedError("OAMDATA register not implemented")
        elif register == REG_PPUSCROLL:
            print >> sys.stderr, 'Warning: read from PPUSCROLL'
        elif register == REG_PPUADDR:
            print >> sys.stderr, 'Warning: read from PPUADDR'
        elif register == REG_PPUDATA:
            pass
        else:
            raise RuntimeError("PPU read from bad register %x" % register)
        return chr(self.latch)

    def writeReg(self, register, val):
        if isinstance(val, str): # someday we will want to get rid of this chr/ord weirdness
            val = ord(val)
        self.latch = val
        if register == REG_PPUCTRL:
            self.nametableBase = val & 0x3 # bits 0,1
            self.vramInc = (val >> 2) & 0x1 # bit 2
            self.spritePatternTableAddr = (val >> 3) & 0x1 # bit 3
            self.bgPatternTableAddr = (val >> 4) & 0x1 # bit 4
            self.spriteSize = (val >> 5) & 0x1 # bit 5
            self.ppuMasterSlave = (val >> 6) & 0x1 # bit 6
            self.vblankNMI = (val >> 7) & 0x1 # bit 7
            # TODO if we just set vblankNMI and we're in vblank, this
            # might be supposed to trigger the NMI
            if self.ppuMasterSlave:
                raise RuntimeError("We set the PPU master/slave bit! That's bad!")
        elif register == REG_PPUMASK:
            print >> sys.stderr, "Ignoring write to PPUMASK for now"
            pass
        elif register == REG_PPUSTATUS:
            print >> sys.stderr, 'Warning: write to PPUSTATUS'
        elif register == REG_OAMADDR:
            self.oamaddr = val
        elif register == REG_OAMDATA:
            raise NotImplementedError("OAMDATA register not implemented")
        elif register == REG_PPUSCROLL:
            if self.nextScroll == 0:
                self.scrollX = val
                self.nextScroll = 1
            else:
                self.scrollY = val
                self.nextScroll = 0
        elif register == REG_PPUADDR:
            pass
        elif register == REG_PPUDATA:
            pass
        else:
            raise RuntimeError("PPU write to bad register %x" % register)

    def ppuTick(self):
        if (self.scanline, self.cycle) == VBLANK_START:
            self.vblank = 1
            if self.vblankNMI:
                # TODO signal NMI
                pass
        elif (self.scanline, self.cycle) == VBLANK_END:
            self.vblank = 0

        # TODO if we're on a visible pixel, draw that pixel
            
        self.cycle = (self.cycles + 1) % CYCLES
        if self.cycles == 0:
            self.scanline = (self.scanlines + 1) % SCANLINES
        # TODO skip cycle 340 on scanline 239 on odd
        # frames... hahahaha no I don't care
