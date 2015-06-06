# Functions for memory addressing go here.

from operator import xor
import struct

# note: 6502 is little-endian

# interrupt vectors
VEC_NMI = 0xFFFA
VEC_RST = 0xFFFC
VEC_IRQ = 0xFFFE

RAM_SIZE = 0x0800

REG_OAMDMA = 0x4014

class Memory(object):

    def __init__(self, cpu):
        # ignoring some special bytes. see:
        # http://wiki.nesdev.com/w/index.php/CPU_power_up_state
        self.cpu = cpu
        self.ram = ['\xff'] * RAM_SIZE

    def readMany(self, address, nbytes):
        out = ""
        for i in range(nbytes):
            out += self.read(address + i)
        return out

    def read(self, address):
        if 0x0 <= address < 0x2000:
            # Internal RAM from $0000 to $07FF; higher addresses here are mirrored
            return self.ram[address % 0x0800]
        elif 0x2000 <= address < 0x4000:
            register = (address - 0x2000) % 8
            raise NotImplementedError("Can't read PPU register %d at 0x%04x: no PPU" %
                                      (register, address))
        elif 0x4000 < address <= 0x4020:
            raise NotImplementedError("APU or I/O register at 0x%04x not implemented" %
                                      address)
        elif 0x4020 <= address <= 0xffff:
            if self.cpu.prgromsize > 0x4000:
                raise NotImplementedError("PRG ROM mapping not implemented")
            # TODO put together a proper mapping:
            # see http://wiki.nesdev.com/w/index.php/MMC1
            # and http://wiki.nesdev.com/w/index.php/UxROM
            prgaddr = address - 0x8000
            if prgaddr >= 0x4000:
                prgaddr -= 0x4000
            return self.cpu.prgrom[prgaddr]
        else:
            raise RuntimeError("Address out of range: %x" % address)

    def write(self, address, val):
        if isinstance(val, int): # someday we will want to get rid of this chr/ord weirdness
            val = chr(val)
        # Lot of copy-pasting between here and read. Not sure how to
        # fix it without like a page table, which is probably more
        # effort than it's worth
        if 0x0 <= address < 0x2000:
            # Internal RAM from $0000 to $07FF; higher addresses here are mirrored
            self.ram[address % 0x0800] = val
        elif 0x2000 <= address < 0x4000:
            register = (address - 0x2000) % 8
            raise NotImplementedError("Can't write PPU register %d at 0x%04x: no PPU" %
                                      (register, address))
        elif 0x4000 < address <= 0x4020:
            raise NotImplementedError("APU or I/O register at 0x%04x not implemented" %
                                      address)
        elif 0x4020 <= address <= 0xffff:
            raise RuntimeError("Tried to write to ROM address %x" % address)
        else:
            raise RuntimeError("Address out of range: %x" % address)
    
    def dereference(self, paddr): # utility function
        """Dereference a 16-bit pointer."""
        pointer = self.readMany(paddr, nbytes=2)
        return struct.unpack("<H", pointer)[0]

class MMC1(Memory):
    # TODO properly structure these classes - right now I'm mostly
    # copy-pasting

    # note: MMC1 variants not supported (SNROM, SOROM, SUROM, SXROM)

    # note: there's some weirdshit with games like bill and ted's
    # excellent adventure where read/modify/write instructions do two
    # writes and only the first counts. that is nowhere near supported
    # here.

    def __init__(self, cpu):
        # ignoring some special bytes. see:
        # http://wiki.nesdev.com/w/index.php/CPU_power_up_state
        self.cpu = cpu
        self.ram = ['\xff'] * RAM_SIZE

        self.shiftIndex = 0
        self.shiftContents = 0x00

        # getting startup state from here:
        # http://forums.nesdev.com/viewtopic.php?t=3665
        #
        # bits are set arbitrarily, except that PRG slot and PRG size
        # should be 1

        # mirroring: 0: one-screen lower bank; 1: one-screen upper
        # bank; 2: vertical; 3: horizontal
        self.mirroring = 0
        # PRG slot: 0: $c000 swappable and $8000 fixed; 1: $c000 fixed
        # and $8000 swappable
        self.PRGSlot = 1
        # PRG size: 0: 32k mode; 1: 16k mode
        self.PRGSize = 1
        # CHR mode: 0: 8k mode; 1: 4k mode
        self.CHRMode = 0
        self.CHRBank0 = 0
        self.CHRBank1 = 0
        self.PRGBank = 0
        self.PRGRAMEnable = False

    # TODO the PPU has its own address space, and the mapper will need
    # to deal with that

    def read(self, address):
        if 0x6000 <= address <= 0x8000:
            raise NotImplementedError("PRG RAM bank not implemented")
        elif 0x8000 <= address <= 0xffff:
            if self.PRGSize:
                bank = self.PRGBank >> 1 # ignore lowest bit
                bankIndex = address & 0x7fff # here banks are 32 KB
                return self.cpu.prgrom[(bank * 0x8000) + bankIndex]
            else:
                # find the bank depending on address and PRG slot. If the
                # PRG slot bit is set, we need to find banks for addresses
                # below 0xc000. Otherwise, we need to find banks for
                # addresses >= 0xc000.
                if xor(bool(address >= 0xc000), bool(self.PRGSlot)):
                    bank = self.PRGBank
                else:
                    bank = -1
                bankIndex = address & 0x3fff # banks are 16 KB
                return self.cpu.prgrom[(bank * 0x4000) + bankIndex]
        else:
            return super(MMC1, self).read(address)

    def write(self, address, val):
        if 0x8000 <= address <= 0xffff:
            reset = bool(val % 0x80)
            if not reset:
                # Set the current bit if the data bit is set
                if bool(val % 0x1):
                    self.shiftContents |= (1 << self.shiftIndex)
                # If we're done, write to the register; otherwise,
                # advance the index
                if self.shiftIndex == 4:
                    self.setMapperRegister(address, self.shiftContents)
                    reset = True
                else:
                    self.shiftIndex += 1
            if reset:
                self.shiftIndex = 0
                self.shiftContents = 0
        else:
            # TODO better structure for this
            super(MMC1, self).write(address, val)

    def setMapperRegister(self, address, val):
        if 0x8000 <= address < 0xa000:
            # bits 0-1 set mirroring
            self.mirroring = val & 0x3
            # bit 2 sets slot select
            self.PRGSlot = (val >> 2) & 0x1
            # bit 3 sets PRG size
            self.PRGSize = (val >> 3) & 0x1
            # bit 4 sets CHR mode
            self.CHRMode = (val >> 4) & 0x1
        elif 0xa000 <= address < 0xc000:
            self.CHRBank0 = val
        elif 0xc000 <= address < 0xe000:
            self.CHRBank1 = val
        elif 0xe000 <= address <= 0xffff:
            # bit 4 sets RAM enable; bits 0-3 set bank
            self.PRGRAMEnable = bool(val & 0x10)
            self.PRGBank = val & 0x0f
        else:
            raise RuntimeError("Bad mapper register address %x" % address)
