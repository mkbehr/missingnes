from enum import IntEnum
import struct
from warnings import warn

class AddrMode(IntEnum):
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
    n_addrs = 13

AM = AddrMode

# Length of specifiers for address mode. Instruction length is this + 1.
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

    def __init__(self, name, f, code, addrMode):
        self.name = name
        self.f = f
        self.code = code
        self.addrMode = addrMode

    @property
    def addrSize(self):
        return ADDR_MODE_LENGTHS[self.addrMode]

    @property
    def size(self):
        return 1 + self.addrSize

class Instruction(object):
    
    def __init__(self, addr, opcode, addrData, rawBytes):
        # Don't call this on its own, use the makeInstr factory method
        self.addr = addr
        self.opcode = opcode
        self.addrData = addrData
        self.rawBytes = rawBytes
        self.memAddrCache = None

    @property
    def size(self):
        return self.opcode.size

    @property
    def nextaddr(self):
        """The address of the next instruction (by listing; doesn't take
        jumps into account)."""
        return self.addr + self.size

    def memAddr(self, cpu):
        """Get the memory address to be written to or read from, using an
        instance-specific cache. We assume an instruction instance
        will never change its memory address.
        """
        if self.memAddrCache is None:
            self.memAddrCache = self.computeMemAddr(cpu)
        return self.memAddrCache

    def computeMemAddr(self, cpu):
        """Returns the memory address to be written to or read from. This will
        depend on the addressing mode."""
        # see http://wiki.nesdev.com/w/index.php/CPU_addressing_modes
        
        # we convert endianness here
        raise RuntimeError("computeMemAddr on abstract Instruction class")

    def readMem(self, cpu):
        #print "reading %x" % ord(cpu.mem.read(self.memAddr(cpu))) # DEBUG
        return cpu.mem.read(self.memAddr(cpu))

    def writeMem(self, val, cpu):
        #print "WRITING to %x" % self.memAddr(cpu) # DEBUG
        cpu.mem.write(self.memAddr(cpu), val)

    def call(self, cpu):
        self.opcode.f(self, cpu)

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
            target = self.addr + offset + 2 # no endianness to worry about
            return "$%04x" % target
        else:
            raise RuntimeError("Unrecognized addressing mode")

    def disassemble(self): # TODO print hex data here too
        return "%04x:    %s %s    %s" % (self.addr,
                                         self.opcode.name,
                                         self.addrDataStr(),
                                         str([hex(ord(b)) for b in self.rawBytes]))

    @staticmethod
    def makeInstr(addr, opcode, addrData, rawBytes):
        cls = AM_CLASSES[opcode.addrMode]
        return cls(addr, opcode, addrData, rawBytes)

class ImpliedAddrInstr(Instruction):
    def computeMemAddr(self, cpu):
        warn("Trying to access memory for implicit-addressing instruction")
        return None

class ImmediateAddrInstr(Instruction):
    def computeMemAddr(self, cpu):
        return self.addr + 1

class ZeroPageAddrInstr(Instruction):
    def computeMemAddr(self, cpu):
        # address high byte is zero (hence "zero page")
        return ord(self.addrData)

class ZeroPageXAddrInstr(Instruction):
    def computeMemAddr(self, cpu):
        return (ord(self.addrData) + cpu.reg_X) % 256

class ZeroPageYAddrInstr(Instruction):
    def computeMemAddr(self, cpu):
        return (ord(self.addrData) + cpu.reg_Y) % 256

class IndirectZeroXAddrInstr(Instruction):
    def computeMemAddr(self, cpu):
        # can't use the dereference utility function for this because
        # we have to stay in the zero page
        pointer = (ord(self.addrData) + cpu.reg_X) % 256
        addrLow = ord(cpu.mem.read(pointer))
        addrHigh = ord(cpu.mem.read((pointer + 1) % 256))
        return addrLow + addrHigh * 256

class IndirectZeroYAddrInstr(Instruction):
    def computeMemAddr(self, cpu):
        pointer = ord(self.addrData)
        addrLow = ord(cpu.mem.read(pointer))
        addrHigh = ord(cpu.mem.read((pointer + 1) % 256))
        return (addrLow + addrHigh * 256 + cpu.reg_Y) & 0xffff

# remember little-endian from here on

class AbsoluteAddrInstr(Instruction):
    def computeMemAddr(self, cpu):
        return struct.unpack('H', self.addrData)[0]

class AbsoluteXAddrInstr(Instruction):
    def computeMemAddr(self, cpu):
        offset = struct.unpack('H', self.addrData)[0]
        return (offset + cpu.reg_X) & 0xffff

class AbsoluteYAddrInstr(Instruction):
    def computeMemAddr(self, cpu):
        offset = struct.unpack('H', self.addrData)[0]
        return (offset + cpu.reg_Y) & 0xffff

class IndexedAddrInstr(Instruction):
    def computeMemAddr(self, cpu):
        pointer = struct.unpack('H', self.addrData)[0]
        addrLow = ord(cpu.mem.read(pointer))
        # 6502 bug? see http://forums.nesdev.com/viewtopic.php?t=5388
        addrHighLoc = pointer + 1
        if (addrHighLoc & 0xff00) != (pointer & 0xff00):
            addrHighLoc -= 0x100
        addrHigh = ord(cpu.mem.read(addrHighLoc))
        return addrLow + addrHigh * 256

class RelativeAddrInstr(Instruction):
    def computeMemAddr(self, cpu):
        # Here addrData is a signed integer that represents an offest
        # from the address we'll reach after the instruction, at least
        # as far as I can tell. No endianness to worry about.
        offset = struct.unpack('b', self.addrData)[0]
        target = self.addr + offset + 2 # lol computers
        return target

AM_CLASSES = [None] * AM.n_addrs
AM_CLASSES[AM.imp] = ImpliedAddrInstr
AM_CLASSES[AM.imm] = ImmediateAddrInstr
AM_CLASSES[AM.zp] = ZeroPageAddrInstr
AM_CLASSES[AM.zpx] = ZeroPageXAddrInstr
AM_CLASSES[AM.zpy] = ZeroPageYAddrInstr
AM_CLASSES[AM.izx] = IndirectZeroXAddrInstr
AM_CLASSES[AM.izy] = IndirectZeroYAddrInstr
AM_CLASSES[AM.abs] = AbsoluteAddrInstr
AM_CLASSES[AM.abx] = AbsoluteXAddrInstr
AM_CLASSES[AM.aby] = AbsoluteYAddrInstr
AM_CLASSES[AM.ind] = IndexedAddrInstr
AM_CLASSES[AM.rel] = RelativeAddrInstr
