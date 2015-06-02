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

make_op("SEI", 0x78, AM.imp)
