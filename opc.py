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
        code = opcodeLookup(ord(mem.addr(address, cpu)))
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

def opcodeLookup(code):
    if code in opcodes:
        return opcodes[code]
    else:
        return Opcode("ILLOP", code, AM.imp)

def make_op(name, code, addrMode):
    # some sanchecking seems worthwhile
    assert code not in opcodes
    assert code >= 0x00
    assert code <= 0xff
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
opFamily("AND",
         0x29, AM.imm,
         0x25, AM.zp,
         0x35, AM.zpx,
         0x21, AM.izx,
         0x31, AM.izy,
         0x2D, AM.abs,
         0x3D, AM.abx,
         0x39, AM.aby)
opFamily("EOR",
         0x49, AM.imm,
         0x45, AM.zp,
         0x55, AM.zpx,
         0x41, AM.izx,
         0x51, AM.izy,
         0x4D, AM.abs,
         0x5D, AM.abx,
         0x59, AM.aby)
opFamily("ADC",
         0x69, AM.imm,
         0x65, AM.zp,
         0x75, AM.zpx,
         0x61, AM.izx,
         0x71, AM.izy,
         0x6D, AM.abs,
         0x7D, AM.abx,
         0x79, AM.aby)
opFamily("SBC",
         0xE9, AM.imm,
         0xE5, AM.zp,
         0xF5, AM.zpx,
         0xE1, AM.izx,
         0xF1, AM.izy,
         0xED, AM.abs,
         0xFD, AM.abx,
         0xF9, AM.aby)
opFamily("CMP",
         0xC9, AM.imm,
         0xC5, AM.zp,
         0xD5, AM.zpx,
         0xC1, AM.izx,
         0xD1, AM.izy,
         0xCD, AM.abs,
         0xDD, AM.abx,
         0xD9, AM.aby)
opFamily("CPX",
         0xE0, AM.imm,
         0xE4, AM.zp,
         0xEC, AM.abs)
opFamily("CPY",
         0xC0, AM.imm,
         0xC4, AM.zp,
         0xCC, AM.abs)
opFamily("DEC",
         0xC6, AM.zp,
         0xD6, AM.zpx,
         0xCE, AM.abs,
         0xDE, AM.abx)
make_op("DEX", 0xCA, AM.imp)
make_op("DEY", 0x88, AM.imp)
opFamily("INC",
         0xE6, AM.zp,
         0xF6, AM.zpx,
         0xEE, AM.abs,
         0xFE, AM.abx)
make_op("INX", 0xE8, AM.imp)
make_op("INY", 0xC8, AM.imp)
opFamily("ASL",
         0x0A, AM.imp,
         0x06, AM.zp,
         0x16, AM.zpx,
         0x0E, AM.abs,
         0x1E, AM.abx)
opFamily("ROL",
         0x2A, AM.imp,
         0x26, AM.zp,
         0x36, AM.zpx,
         0x2E, AM.abs,
         0x3E, AM.abx)
opFamily("LSR",
         0x4A, AM.imp,
         0x46, AM.zp,
         0x56, AM.zpx,
         0x4E, AM.abs,
         0x5E, AM.abx)
opFamily("ROR",
         0x6A, AM.imp,
         0x66, AM.zp,
         0x76, AM.zpx,
         0x6E, AM.abs,
         0x7E, AM.abx)

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
opFamily("STX",
         0x86, AM.zp,
         0x96, AM.zpy,
         0x8E, AM.abs)
opFamily("LDY",
         0xA0, AM.imm,
         0xA4, AM.zp,
         0xB4, AM.zpx,
         0xAC, AM.abs,
         0xBC, AM.abx)
opFamily("STY",
         0x84, AM.zp,
         0x94, AM.zpx,
         0x8C, AM.abs)
make_op("TAX", 0xAA, AM.imp)
make_op("TXA", 0x8A, AM.imp)
make_op("TAY", 0xA8, AM.imp)
make_op("TYA", 0x98, AM.imp)
make_op("TSX", 0xBA, AM.imp)
make_op("TXS", 0x9A, AM.imp)
make_op("PLA", 0x68, AM.imp)
make_op("PHA", 0x48, AM.imp)
make_op("PLP", 0x28, AM.imp)
make_op("PHP", 0x08, AM.imp)

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
