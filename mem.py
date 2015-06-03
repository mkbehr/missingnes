# Functions for memory addressing go here.

import struct

from enum import Enum

# note: 6502 is little-endian

# interrupt vectors
VEC_NMI = 0xFFFA
VEC_RST = 0xFFFC
VEC_IRQ = 0xFFFE

RAM_SIZE = 0x0800

class Memory(object):

    def __init__(self, cpu):
        # ignoring some special bytes. see:
        # http://wiki.nesdev.com/w/index.php/CPU_power_up_state
        self.cpu = cpu
        self.ram = ['\xff'] * RAM_SIZE


    def read(self, address, nbytes=1):
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
            return self.cpu.prgrom[prgaddr:prgaddr+nbytes]
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
        pointer = self.read(paddr, nbytes=2)
        return struct.unpack("<H", pointer)[0]

class AddrMode(Enum):
    imp = 1 # implicit
    imm = 2 # immediate
    zp = 3 # zero page
    zpx = 4 # zero page, X
    zpy = 5 # zero page, Y
    izx = 6 # indirect, X
    izy = 7 # indirect, Y
    abs = 8 # absolute
    abx = 9 # absolute, X
    aby = 10 # absolute, Y
    ind = 11 # indexed
    rel = 12 # relative
