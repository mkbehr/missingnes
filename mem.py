# Functions for memory addressing go here.

# note: 6502 is little-endian

# interrupt vectors
VEC_NMI = 0xFFFA
VEC_RST = 0xFFFC
VEC_IRQ = 0xFFFE

# TODO organize this functionality reasonably
def addr(address, cpu):
    if address >= 0x8000:
        if cpu.prgromsize > 0x4000:
            raise NotImplementedError("PRG ROM mapping not implemented")
        # TODO put together a proper mapping
        prgaddr = address - 0x8000
        if prgaddr >= 0x4000:
            prgaddr -= 0x4000
        return cpu.prgrom[prgaddr]
    else:
        raise NotImplementedError("Can only access PRG ROM")
    
