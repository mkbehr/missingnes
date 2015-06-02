import mem
import struct

AM = mem.AddrMode

# Length of specifiers for address mode. Operation length is this + 1.
ADDR_MODE_LENGTHS = {
    AM.imp : 0,
    AM.imm : 1,
    AM.zp : 1,
    AM.zpx : 1,
    AM.zpy : 1,
    AM.izx : 1,
    AM.izy : 1,
    AM.abs : 2,
    AM.abx : 2,
    AM.aby : 2,
    AM.ind : 2,
    AM.rel : 1,
    }

class Opcode(object):

    def __init__(self, name, code, addrMode): # TODO functions
        self.name = name
        self.code = code
        self.addrMode = addrMode

    @property
    def addrSize(self):
        return ADDR_MODE_LENGTHS[self.addrMode]

    @property
    def size(self):
        return 1 + self.addrSize

class Operation(object):
    
    def __init__(self, addr, opcode, addrData):
        # TODO address-mode-relevant information
        # TODO should this store its own address?
        self.addr = addr
        self.opcode = opcode
        self.addrData = addrData

    @property
    def size(self):
        return self.opcode.size

    @property
    def nextaddr(self):
        """The address of the next operation (by listing; doesn't take
        jumps into account)."""
        return self.addr + self.size

    def addrDataStr(self):
        # This probably could have been shorter. Oh well.
        am = self.opcode.addrMode
        if am == AM.imp:
            return ""
        elif am == AM.imm:
            return "#$%02x" % ord(self.addrData)
        elif am == AM.zp:
            return "$%02x" % ord(self.addrData)
        elif am == AM.zpx:
            return "$%02x, X" % ord(self.addrData)
        elif am == AM.zpy:
            return "$%02x, Y" % ord(self.addrData)
        elif am == AM.izx:
            return "($%02x, X)" % ord(self.addrData)
        elif am == AM.izy:
            return "($%02x), Y" % ord(self.addrData)
        # remember little-endian from here on
        elif am == AM.abs:
            return "$%02x%02x" % (ord(self.addrData[1]),
                                  ord(self.addrData[0]))
        elif am == AM.abx:
            return "$%02x%02x, X" % (ord(self.addrData[1]),
                                     ord(self.addrData[0]))
        elif am == AM.aby:
            return "$%02x%02x, Y" % (ord(self.addrData[1]),
                                     ord(self.addrData[0]))
        elif am == AM.ind:
            return "($%02x%02x)" % (ord(self.addrData[1]),
                                    ord(self.addrData[0]))
        elif am == AM.rel:
            # here addrData is a signed integer that represents an
            # offest from the address we'll reach after the
            # instruction, at least as far as I can tell
            offset = struct.unpack('b', self.addrData)[0]
            target = self.addr + offset # no endianness to worry about
            return "$%04x" % target
        else:
            raise RuntimeError("Unrecognized addressing mode")

    def disassemble(self): # TODO print hex data here too
        return "%04x:    %s %s" % (self.addr,
                                   self.opcode.name,
                                   self.addrDataStr())

    @staticmethod
    def fromAddr(address, cpu):
        code = opcodes[ord(mem.addr(address, cpu))]
        addrData = mem.addr(address+1, cpu, nbytes = code.addrSize)
        return Operation(address, code, addrData)

    @staticmethod
    def listFromAddr(address, nops, cpu):
        out = []
        while nops:
            op = Operation.fromAddr(address, cpu)
            out.append(op)
            nops -= 1
            address += op.size
        return out

opcodes = {}

def make_op(name, code, addrMode):
    opcodes[code] = Opcode(name, code, addrMode)

def opFamily(name, *args):
    if (len(args) % 2):
        raise RuntimeError("opFamily needs an even number of args")
    for i in range(len(args)/2):
        make_op(name, args[2*i], args[(2*i)+1])    

## Begin opcode listing
# see http://www.oxyron.de/html/opcodes02.html

# Logical and arithmetic commands
opFamily("ORA",
         0x09, AM.imm,
         0x05, AM.zp,
         0x15, AM.zpx,
         0x01, AM.izx,
         0x11, AM.izy,
         0x0D, AM.abs,
         0x1D, AM.abx,
         0x19, AM.aby)
# TODO and, eor, adc, sbc, cmp, cpx, cpy, dec, dex, dey, inc, inx,
# iny, asl, rol, lsr, ror

# Move commands

opFamily("LDA",
         0xA9, AM.imm,
         0xA5, AM.zp,
         0xB5, AM.zpx,
         0xA1, AM.izx,
         0xB1, AM.izy,
         0xAD, AM.abs,
         0xBD, AM.abx,
         0xB9, AM.aby)
opFamily("STA",
         0x85, AM.zp,
         0x95, AM.zpx,
         0x81, AM.izx,
         0x91, AM.izy,
         0x8D, AM.abs,
         0x9D, AM.abx,
         0x99, AM.aby)
opFamily("LDX",
         0xA2, AM.imm,
         0xA6, AM.zp,
         0xB6, AM.zpy,
         0xAE, AM.abs,
         0xBE, AM.aby)

# TODO stx, ldy, sty, tax, txa, tay, tya, tsx

make_op("TXS", 0x9A, AM.imp)

# TODO pla, pha, plp, php

# Jump/flag commands

make_op("BPL", 0x10, AM.rel)
make_op("BMI", 0x30, AM.rel)
make_op("BVC", 0x50, AM.rel)
make_op("BVS", 0x70, AM.rel)
make_op("BCC", 0x90, AM.rel)
make_op("BCS", 0xB0, AM.rel)
make_op("BNE", 0xD0, AM.rel)
make_op("BEQ", 0xF0, AM.rel)
make_op("BRK", 0x00, AM.imp)
make_op("RTI", 0x40, AM.imp)
make_op("JSR", 0x20, AM.abs)
make_op("RTS", 0x60, AM.imp)
opFamily("JMP",
         0x4C, AM.abs,
         0x6C, AM.ind)
opFamily("BIT",
         0x24, AM.zp,
         0x2C, AM.abs)
make_op("CLC", 0x18, AM.imp)
make_op("SEC", 0x38, AM.imp)
make_op("CLD", 0xD8, AM.imp)
make_op("SED", 0xF8, AM.imp)
make_op("CLI", 0x58, AM.imp)
make_op("SEI", 0x78, AM.imp)
make_op("CLV", 0xB8, AM.imp)
make_op("NOP", 0xEA, AM.imp)

# Illegal opcodes

# TODO fuck it just make them ILLOP, at least for now
