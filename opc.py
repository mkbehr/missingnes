import mem

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
    
    def __init__(self, opcode, addrData):
        # TODO address-mode-relevant information
        # TODO should this store its own address?
        self.opcode = opcode
        self.addrData = addrData

    @property
    def size(self):
        return self.opcode.size

    def disassemble(self):
        if self.size > 1: # do we have arguments?
            return "%s %s" % (self.opcode.name, self.addrData)
        else:
            return self.opcode.name

    @staticmethod
    def fromAddr(address, cpu):
        code = opcodes[ord(mem.addr(address, cpu))]
        addrData = mem.addr(address+1, cpu, nbytes = code.addrSize)
        return Operation(code, addrData)

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

# TODO sta

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

# TODO bpl, bmi, bvc, bvs, bcc, bcs, bne, beq, brk, rti, jsr, rts,
# jmp, bit, clc, sec

make_op("CLD", 0xD8, AM.imp)

# TODO sed, cli, sei, clv, nop

# Illegal opcodes

# TODO fuck it just make them ILLOP, at least for now

make_op("SEI", 0x78, AM.imp)
