# Functions for memory addressing go here.

import struct

from enum import Enum

# note: 6502 is little-endian

# interrupt vectors
VEC_NMI = 0xFFFA
VEC_RST = 0xFFFC
VEC_IRQ = 0xFFFE

# TODO organize this functionality reasonably
def addr(address, cpu, nbytes=1):
    if address >= 0x8000:
        if cpu.prgromsize > 0x4000:
            raise NotImplementedError("PRG ROM mapping not implemented")
        # TODO put together a proper mapping:
        # see http://wiki.nesdev.com/w/index.php/MMC1
        # and http://wiki.nesdev.com/w/index.php/UxROM
        prgaddr = address - 0x8000
        if prgaddr >= 0x4000:
            prgaddr -= 0x4000
        return cpu.prgrom[prgaddr:prgaddr+nbytes]
    else:
        raise NotImplementedError("Can only access PRG ROM")
    
def dereference(paddr, cpu):
    """Dereference a 16-bit pointer."""
    pointer = addr(paddr, cpu, nbytes=2)
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
