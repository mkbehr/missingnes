import cpu as c
import mem
import struct

from warnings import warn

AM = mem.AddrMode

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
    
    def __init__(self, addr, opcode, addrData):
        self.addr = addr
        self.opcode = opcode
        self.addrData = addrData

    @property
    def size(self):
        return self.opcode.size

    @property
    def nextaddr(self):
        """The address of the next instruction (by listing; doesn't take
        jumps into account)."""
        return self.addr + self.size

    def memAddr(self):
        """Returns the memory address to be written to or read from. This will
        depend on the addressing mode."""
        # we convert endianness here
        am = self.opcode.addrMode
        if am == AM.imp:
            warn("Trying to access memory for implicit-addressing instruction")
            return None
        elif am == AM.imm:
            return self.addr + 1
        elif am == AM.zp:
            return ord(self.addrData) # address high byte is zero (hence "zero page")
        elif am == AM.zpx:
            raise NotImplementedError()

        elif am == AM.zpy:
            raise NotImplementedError()

        elif am == AM.izx:
            raise NotImplementedError()

        elif am == AM.izy:
            raise NotImplementedError()

        # remember little-endian from here on
        elif am == AM.abs:
            return struct.unpack('H', self.addrData)[0]
        elif am == AM.abx:
            raise NotImplementedError()

        elif am == AM.aby:
            raise NotImplementedError()

        elif am == AM.ind:
            raise NotImplementedError()

        elif am == AM.rel:
            # here addrData is a signed integer that represents an
            # offest from the address we'll reach after the
            # instruction, at least as far as I can tell
            offset = struct.unpack('b', self.addrData)[0]
            target = self.addr + offset # no endianness to worry about
            return target
        else:
            raise RuntimeError("Unrecognized addressing mode")

    def readMem(self, cpu):
        return cpu.mem.read(self.memAddr())

    def writeMem(self, val, cpu):
        cpu.mem.write(self.memAddr(), val)

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
        code = opcodeLookup(ord(cpu.mem.read(address)))
        addrData = cpu.mem.read(address+1, nbytes = code.addrSize)
        return Instruction(address, code, addrData)

    @staticmethod
    def listFromAddr(address, nops, cpu):
        out = []
        while nops:
            op = Instruction.fromAddr(address, cpu)
            out.append(op)
            nops -= 1
            address += op.size
        return out

opcodes = {}

def op_illop(instr, cpu):
    raise RuntimeError("Illegal or unimplemented operation %s (%x) at %x" % (instr.opcode.name,
                                                                             instr.opcode.code,
                                                                             instr.addr))
def opcodeLookup(code):
    if code in opcodes:
        return opcodes[code]
    else:
        return Opcode("ILLOP", op_illop, code, AM.imp)

def make_op(name, f, code, addrMode):
    # some sanchecking seems worthwhile
    assert code not in opcodes
    assert code >= 0x00
    assert code <= 0xff
    opcodes[code] = Opcode(name, f, code, addrMode)

def opFamily(name, f, *args):
    if (len(args) % 2):
        raise RuntimeError("opFamily needs an even number of args")
    for i in range(len(args)/2):
        make_op(name, f, args[2*i], args[(2*i)+1])    

## Begin opcode listing
# see http://www.oxyron.de/html/opcodes02.html

# Logical and arithmetic commands
def op_ora(instr, cpu):
    memval = ord(instr.readMem(cpu))
    out = cpu.reg_A | memval
    cpu.reg_A = out
    cpu.mathFlags(out)
opFamily("ORA", op_ora,
         0x09, AM.imm,
         0x05, AM.zp,
         0x15, AM.zpx,
         0x01, AM.izx,
         0x11, AM.izy,
         0x0D, AM.abs,
         0x1D, AM.abx,
         0x19, AM.aby)

def op_and(instr, cpu):
    memval = ord(instr.readMem(cpu))
    out = cpu.reg_A & memval
    cpu.reg_A = out
    cpu.mathFlags(out)
opFamily("AND", op_and,
         0x29, AM.imm,
         0x25, AM.zp,
         0x35, AM.zpx,
         0x21, AM.izx,
         0x31, AM.izy,
         0x2D, AM.abs,
         0x3D, AM.abx,
         0x39, AM.aby)

def op_eor(instr, cpu):
    memval = ord(instr.readMem(cpu))
    out = cpu.reg_A ^ memval
    cpu.reg_A = out
    cpu.mathFlags(out)
opFamily("EOR", op_eor,
         0x49, AM.imm,
         0x45, AM.zp,
         0x55, AM.zpx,
         0x41, AM.izx,
         0x51, AM.izy,
         0x4D, AM.abs,
         0x5D, AM.abx,
         0x59, AM.aby)

def op_adc(instr, cpu):
    # Add the specified memory contents and the carry bit to the
    # accumulator (and set appropriate flags).
    #
    # The 6502 specifies that this and subtraction should use
    # binary-coded decimal if the D flag is set, but the NES's 2A03
    # doesn't include decimal mode so we can ignore that.
    #
    # The carry flag represents carrying when the unsigned result
    # wouldn't fit in a byte, and the overflow flag represents
    # changing the sign (7th bit) of the accumulator.
    oldA = cpu.reg_A
    addend = instr.readMem(cpu)
    result = oldA + addend
    if cpu.flag(c.FLAG_C):
        result += 1
    if result > 0xff:
        result &= 0xff
        cpu.setFlag(c.FLAG_C, True)
    else:
        cpu.setFlag(c.FLAG_C, False)
    cpu.setFlag(c.FLAG_V,
                (oldA & 0x80) == (addend & 0x80) and
                (result & 0x80) != (oldA & 0x80))
    cpu.reg_A = result
    cpu.mathFlags(result)
opFamily("ADC", op_adc,
         0x69, AM.imm,
         0x65, AM.zp,
         0x75, AM.zpx,
         0x61, AM.izx,
         0x71, AM.izy,
         0x6D, AM.abs,
         0x7D, AM.abx,
         0x79, AM.aby)

def op_sbc(instr, cpu):
    oldA = cpu.reg_A
    addend = instr.readMem(cpu)
    # get -M with two's complement (this will map 0x80 to 0x80 but
    # don't worry about it)
    subtractend = (addend ^ 0xff) + 1
    result = oldA + subtractend
    if not cpu.flag(c.FLAG_C):
        result -= 1
    if result > 0xff:
        result &= 0xff
        cpu.setFlag(c.FLAG_C, True)
    else:
        cpu.setFlag(c.FLAG_C, False)
    cpu.setFlag(c.FLAG_V,
                (oldA & 0x80) == (subtractend & 0x80) and
                (result & 0x80) != (oldA & 0x80))
    cpu.reg_A = result
    cpu.mathFlags(result)
opFamily("SBC", op_sbc,
         0xE9, AM.imm,
         0xE5, AM.zp,
         0xF5, AM.zpx,
         0xE1, AM.izx,
         0xF1, AM.izy,
         0xED, AM.abs,
         0xFD, AM.abx,
         0xF9, AM.aby)

def cmpHelper(a, b, cpu):
    negb = (b ^ 0xff) + 1
    result = a + negb + 1
    cpu.setFlag(c.FLAG_C, result > 0xff)
    cpu.setFlag(c.FLAG_Z, result == 0)
    cpu.setFlag(c.FLAG_N, result & 0x80)

def op_cmp(instr, cpu):
    cmpHelper(cpu.reg_A, instr.readMem(cpu))
opFamily("CMP", op_cmp,
         0xC9, AM.imm,
         0xC5, AM.zp,
         0xD5, AM.zpx,
         0xC1, AM.izx,
         0xD1, AM.izy,
         0xCD, AM.abs,
         0xDD, AM.abx,
         0xD9, AM.aby)

def op_cpx(instr, cpu):
    cmpHelper(cpu.reg_X, instr.readMem(cpu))
opFamily("CPX", op_cpx,
         0xE0, AM.imm,
         0xE4, AM.zp,
         0xEC, AM.abs)

def op_cpy(instr, cpu):
    cmpHelper(cpu.reg_Y, instr.readMem(cpu))
opFamily("CPY", op_cpy,
         0xC0, AM.imm,
         0xC4, AM.zp,
         0xCC, AM.abs)

def op_dec(instr, cpu):
    val = ord(instr.readMem(cpu)) - 1
    if val < 0x0:
        val = 0xff
    instr.writeMem(val, cpu)
    cpu.mathFlags(val)
opFamily("DEC", op_dec,
         0xC6, AM.zp,
         0xD6, AM.zpx,
         0xCE, AM.abs,
         0xDE, AM.abx)

def op_dex(instr, cpu):
    val = cpu.reg_X + 1
    if val < 0x0:
        val = 0xff
    cpu.reg_X = val
    cpu.mathFlags(val)
make_op("DEX", op_dex, 0xCA, AM.imp)

def op_dey(instr, cpu):
    val = cpu.reg_Y + 1
    if val < 0x0:
        val = 0xff
    cpu.reg_Y = val
    cpu.mathFlags(val)
make_op("DEY", op_dey, 0x88, AM.imp)

def op_inc(instr, cpu):
    val = ord(instr.readMem(cpu)) + 1
    if val > 0xff:
        val = 0
    instr.writeMem(val, cpu)
    cpu.mathFlags(val)
opFamily("INC", op_inc,
         0xE6, AM.zp,
         0xF6, AM.zpx,
         0xEE, AM.abs,
         0xFE, AM.abx)

def op_inx(instr, cpu):
    val = cpu.reg_X + 1
    if val > 0xff:
        val = 0
    cpu.reg_X = val
    cpu.mathFlags(val)
make_op("INX", op_inx, 0xE8, AM.imp)

op_iny = op_illop
def op_iny(instr, cpu):
    val = cpu.reg_Y + 1
    if val > 0xff:
        val = 0
    cpu.reg_Y = val
    cpu.mathFlags(val)
make_op("INY", op_iny, 0xC8, AM.imp)

def op_asl(instr, cpu):
    # Shift memory or accumulator one bit left, storing bit 7 in carry
    # flag
    if instr.opcode.addrMode == AM.imp:
        input = cpu.reg_A
    else:
        input = ord(instr.readMem(cpu))
    cpu.setFlag(c.FLAG_C, input & 0x80)
    output = (input << 1) & 0xff
    cpu.mathFlags(output)
    if instr.opcode.addrMode == AM.imp:
        cpu.reg_A = output
    else:
        instr.writeMem(output, cpu)
opFamily("ASL", op_asl,
         0x0A, AM.imp,
         0x06, AM.zp,
         0x16, AM.zpx,
         0x0E, AM.abs,
         0x1E, AM.abx)

def op_rol(instr, cpu):
    # Rotate memory or accumulator one bit left, placing old bit 7 in
    # new bit 0
    if instr.opcode.addrMode == AM.imp:
        input = cpu.reg_A
    else:
        input = ord(instr.readMem(cpu))
    output = (input << 1) & 0xff
    if input & 0x80:
        output |= 0x1
    cpu.mathFlags(output)
    if instr.opcode.addrMode == AM.imp:
        cpu.reg_A = output
    else:
        instr.writeMem(output, cpu)
opFamily("ROL", op_rol,
         0x2A, AM.imp,
         0x26, AM.zp,
         0x36, AM.zpx,
         0x2E, AM.abs,
         0x3E, AM.abx)

def op_lsr(instr, cpu):
    # Shift memory or accumulator one bit right, storing bit 0 in
    # carry flag
    if instr.opcode.addrMode == AM.imp:
        input = cpu.reg_A
    else:
        input = ord(instr.readMem(cpu))
    cpu.setFlag(c.FLAG_C, input & 0x01)
    output = input >> 1
    cpu.mathFlags(output)
    if instr.opcode.addrMode == AM.imp:
        cpu.reg_A = output
    else:
        instr.writeMem(output, cpu)
opFamily("LSR", op_lsr,
         0x4A, AM.imp,
         0x46, AM.zp,
         0x56, AM.zpx,
         0x4E, AM.abs,
         0x5E, AM.abx)

def op_ror(instr, cpu):
    # Rotate memory or accumulator one bit right, placing old bit 0 in
    # new bit 7
    if instr.opcode.addrMode == AM.imp:
        input = cpu.reg_A
    else:
        input = ord(instr.readMem(cpu))
    output = input >> 1
    if input & 0x01:
        output |= 0x80
    cpu.mathFlags(output)
    if instr.opcode.addrMode == AM.imp:
        cpu.reg_A = output
    else:
        instr.writeMem(output, cpu)
opFamily("ROR", op_ror,
         0x6A, AM.imp,
         0x66, AM.zp,
         0x76, AM.zpx,
         0x6E, AM.abs,
         0x7E, AM.abx)

# Move commands

def op_lda(instr, cpu):
    val = ord(instr.readMem(cpu))
    cpu.reg_A = val
    cpu.mathFlags(val)
opFamily("LDA", op_lda,
         0xA9, AM.imm,
         0xA5, AM.zp,
         0xB5, AM.zpx,
         0xA1, AM.izx,
         0xB1, AM.izy,
         0xAD, AM.abs,
         0xBD, AM.abx,
         0xB9, AM.aby)

def op_sta(instr, cpu):
    instr.writeMem(cpu.reg_A, cpu)
opFamily("STA", op_sta,
         0x85, AM.zp,
         0x95, AM.zpx,
         0x81, AM.izx,
         0x91, AM.izy,
         0x8D, AM.abs,
         0x9D, AM.abx,
         0x99, AM.aby)

def op_ldx(instr, cpu):
    val = ord(instr.readMem(cpu))
    cpu.reg_X = val
    cpu.mathFlags(val)
opFamily("LDX", op_ldx,
         0xA2, AM.imm,
         0xA6, AM.zp,
         0xB6, AM.zpy,
         0xAE, AM.abs,
         0xBE, AM.aby)

def op_stx(instr, cpu):
    instr.writeMem(cpu.reg_X, cpu)
opFamily("STX", op_stx,
         0x86, AM.zp,
         0x96, AM.zpy,
         0x8E, AM.abs)

def op_ldy(instr, cpu):
    val = ord(instr.readMem(cpu))
    cpu.reg_Y = val
    cpu.mathFlags(val)
opFamily("LDY", op_ldy,
         0xA0, AM.imm,
         0xA4, AM.zp,
         0xB4, AM.zpx,
         0xAC, AM.abs,
         0xBC, AM.abx)

def op_sty(instr, cpu):
    instr.writeMem(cpu.reg_Y, cpu)
opFamily("STY", op_sty,
         0x84, AM.zp,
         0x94, AM.zpx,
         0x8C, AM.abs)

def op_tax(instr, cpu):
    cpu.reg_X = cpu.reg_A
    cpu.mathFlags(cpu.reg_X)
make_op("TAX", op_tax, 0xAA, AM.imp)

def op_txa(instr, cpu):
    cpu.reg_A = cpu.reg_X
    cpu.mathFlags(cpu.reg_A)
make_op("TXA", op_txa, 0x8A, AM.imp)

def op_tay(instr, cpu):
    cpu.reg_Y = cpu.reg_A
    cpu.mathFlags(cpu.reg_Y)
make_op("TAY", op_tay, 0xA8, AM.imp)

def op_tya(instr, cpu):
    cpu.reg_A = cpu.reg_Y
    cpu.mathFlags(cpu.reg_A)
make_op("TYA", op_tya, 0x98, AM.imp)

def op_tsx(instr, cpu):
    cpu.reg_X = cpu.reg_S
    cpu.mathFlags(cpu.reg_X)
make_op("TSX", op_tsx, 0xBA, AM.imp)

def op_txs(instr, cpu):
    cpu.reg_S = cpu.reg_X
    cpu.mathFlags(cpu.reg_S)
make_op("TXS", op_txs, 0x9A, AM.imp)

def op_pla(instr, cpu):
    cpu.reg_A = ord(cpu.stackPop())
    cpu.mathFlags(cpu.reg_A)
make_op("PLA", op_pla, 0x68, AM.imp)

def op_pla(instr, cpu):
    cpu.stackPush(cpu.reg_A)
make_op("PHA", op_pha, 0x48, AM.imp)

def op_plp(instr, cpu):
    cpu.flags = ord(cpu.stackPop())
    cpu.setFlag(c.FLAG_B, False)
make_op("PLP", op_plp, 0x28, AM.imp)

def op_php(instr, cpu):
    # according to
    # http://wiki.nesdev.com/w/index.php/CPU_status_flag_behavior this
    # should set B to 1
    flagsToPush = cpu | c.FLAG_B
    cpu.stackPush(flagsToPush)
make_op("PHP", op_php, 0x08, AM.imp)

# Jump/flag commands

def op_bpl(instr, cpu):
    if not cpu.flag(c.FLAG_N):
        cpu.PC = instr.memAddr()
make_op("BPL", op_bpl, 0x10, AM.rel)

def op_bmi(instr, cpu):
    if cpu.flag(c.FLAG_N):
        cpu.PC = instr.memAddr()
make_op("BMI", op_bmi, 0x30, AM.rel)

def op_bvc(instr, cpu):
    if not cpu.flag(c.FLAG_V):
        cpu.PC = instr.memAddr()
make_op("BVC", op_bvc, 0x50, AM.rel)

def op_bvs(instr, cpu):
    if cpu.flag(c.FLAG_V):
        cpu.PC = instr.memAddr()
make_op("BVS", op_bvs, 0x70, AM.rel)

def op_bcc(instr, cpu):
    if not cpu.flag(c.FLAG_C):
        cpu.PC = instr.memAddr()
make_op("BCC", op_bcc, 0x90, AM.rel)

def op_bcs(instr, cpu):
    if cpu.flag(c.FLAG_C):
        cpu.PC = instr.memAddr()
make_op("BCS", op_bcs, 0xB0, AM.rel)

def op_bne(instr, cpu):
    if not cpu.flag(c.FLAG_Z):
        cpu.PC = instr.memAddr()
make_op("BNE", op_bne, 0xD0, AM.rel)

def op_beq(instr, cpu):
    if cpu.flag(c.FLAG_Z):
        cpu.PC = instr.memAddr()
make_op("BEQ", op_beq, 0xF0, AM.rel)

def op_brk(instr, cpu):
    # Trigger an interrupt. Similar to JSR, but it also pushes the
    # flags register and then sets the I flag. The flags register as
    # pushed will have the B flag set. The interrupt vector is the IRQ
    # vector at 0xFFFE.
    toPush = instr.addr + 2
    # Yes, we are pushing PC + 2 even though the instruction is one
    # byte long. Have fun, user! ...okay this says there's a padding byte:
    # http://nesdev.com/the%20%27B%27%20flag%20&%20BRK%20instruction.txt
    toPushHigh = toPush >> 8
    toPushLow = toPush & 0xff
    cpu.stackPush(toPushHigh)
    cpu.stackPush(toPushLow)
    flagsToPush = cpu.flags | c.FLAG_B
    cpu.stackPush(flagsToPush)
    cpu.setFlag(c.FLAG_I, True)
    cpu.PC = cpu.mem.dereference(mem.VEC_IRQ)
make_op("BRK", op_brk, 0x00, AM.imp)

def op_rti(instr, cpu):
    # pop flags, then PC
    cpu.flags = ord(cpu.stackPop())
    cpu.setFlag(c.FLAG_B, False)
    pcLow = ord(cpu.stackPop())
    pcHigh = ord(cpu.stackPop())
    oldpc = pcLow + (pcHigh << 8)
    cpu.PC = oldpc + 1
make_op("RTI", op_rti, 0x40, AM.imp)

def op_jsr(instr, cpu):
    # Note: the spec says (PC + 1) -> PCL; (PC + 1) -> PCH, but it
    # looks like that's a typo. In section 8.1 it says (PC + 1) ->
    # PCL; (PC + 2) -> PCH, which makes more sense.

    # Note that PC is two bytes wide, so we push the high byte and
    # then the low byte.
    toPush = instr.addr + 2
    toPushHigh = toPush >> 8
    toPushLow = toPush & 0xff
    cpu.stackPush(toPushHigh)
    cpu.stackPush(toPushLow)
    cpu.PC = instr.memAddr()
make_op("JSR", op_jsr, 0x20, AM.abs)

def op_rts(instr, cpu):
    # Note: this is defined to pop the PC from the stack and add 1 to
    # it. The stack is properly set up to do this by JSR.
    pcLow = ord(cpu.stackPop())
    pcHigh = ord(cpu.stackPop())
    oldpc = pcLow + (pcHigh << 8)
    cpu.PC = oldpc + 1
make_op("RTS", op_rts, 0x60, AM.imp)

def op_jmp(instr, cpu):
    cpu.PC = instr.memAddr()
opFamily("JMP", op_jmp,
         0x4C, AM.abs,
         0x6C, AM.ind)

def op_bit(instr, cpu):
    mem = ord(instr.readMem(cpu))
    # note that setFlag interprets its arg as a boolean
    cpu.setFlag(c.FLAG_V, mem & 0x40)
    cpu.setFlag(c.FLAG_N, mem & 0x80)
    cpu.setFlag(c.FLAG_Z, not (mem & cpu.reg_A))
opFamily("BIT", op_bit,
         0x24, AM.zp,
         0x2C, AM.abs)

def op_clc(instr, cpu):
    cpu.setFlag(c.FLAG_C, False)
make_op("CLC", op_clc, 0x18, AM.imp)

def op_sec(instr, cpu):
    cpu.setFlag(c.FLAG_C, True)
make_op("SEC", op_sec, 0x38, AM.imp)

def op_cld(instr, cpu):
    cpu.setFlag(c.FLAG_D, False)
make_op("CLD", op_cld, 0xD8, AM.imp)

def op_sed(instr, cpu):
    cpu.setFlag(c.FLAG_D, True)
make_op("SED", op_sed, 0xF8, AM.imp)

def op_cli(instr, cpu):
    cpu.setFlag(c.FLAG_I, False)
make_op("CLI", op_cli, 0x58, AM.imp)

def op_sei(instr, cpu):
    cpu.setFlag(c.FLAG_I, True)
make_op("SEI", op_sei, 0x78, AM.imp)

def op_clv(instr, cpu):
    cpu.setFlag(c.FLAG_V, False)
make_op("CLV", op_clv, 0xB8, AM.imp)

def op_nop(instr, cpu):
    pass
make_op("NOP", op_nop, 0xEA, AM.imp)
