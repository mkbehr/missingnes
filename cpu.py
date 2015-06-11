import mem
import opc
import ppu

import sys

STACK_BASE = 0x100

FLAG_C = 0x1 # carry
FLAG_Z = 0x2 # zero result
FLAG_I = 0x4 # interrupt disable
FLAG_D = 0x8 # decimal mode
FLAG_B = 0x10 # break command
FLAG_EXP = 0x20 # expansion
FLAG_V = 0x40 # overflow
FLAG_N = 0x80 # negative result

class CPU(object):

    def __init__(self, prgrom, chrrom, mapper=0):
        """Sets up an initial CPU state loading from the given ROM. Simulates
        the reset signal."""
        # see http://wiki.nesdev.com/w/index.php/CPU_power_up_state
        # for some initial values
        self.prgrom = prgrom
        self.prgromsize = len(prgrom)
        self.chrrom = chrrom
        self.chrromsize = len(chrrom)
        if mapper == 0:
            self.mem = mem.Memory(self)
        elif mapper == 1:
            self.mem = mem.MMC1(self)
        else:
            raise NotImplementedError("Unimplemented mapper %d" % mapper)

        # registers
        self.reg_A = 0
        self.reg_X = 0
        self.reg_Y = 0

        # stack pointer
        self.SP = 0xFD

        # flags
        self.flags = FLAG_I | FLAG_B | FLAG_EXP

        # program counter: initialize to 0; later set according to the
        # reset signal handler
        self.PC = 0

        # TODO also add RST to this
        self.irqPending = False
        self.nmiPending = False

        self.ppu = ppu.PPU(self)

        # Now that everything is set up, simulate the RST signal.
        # If we ever track frames, this will affect those.
        self.PC = self.mem.dereference(mem.VEC_RST)

    def flag(self, mask):
        return bool(self.flags & mask)

    def setFlag(self, mask, val): # val should be boolean
        if val:
            self.flags |= mask
        else:
            self.flags &= (0xFF ^ mask)

    def mathFlags(self, val):
        self.setFlag(FLAG_Z, val == 0)
        # FLAG_N is set to match bit 7 of the value
        self.setFlag(FLAG_N, val & 0x80)

    # do stack pushing and popping actually want to live in the CPU?
    def stackPush(self, val):
        # TODO make sure the stack pointer stays in a sane range. Some
        # sort of consistency check? Properties that can only have
        # limited values assigned to them?
        self.mem.write(STACK_BASE + self.SP, val)
        self.SP -= 1

    def stackPop(self):
        self.SP += 1
        return self.mem.read(STACK_BASE + self.SP)

    def printState(self):
        print ("A = %02x X = %02x Y = %02x SP=%02x flags = %02x PC = %04x" %
               (self.reg_A, self.reg_X, self.reg_Y, self.SP, self.flags, self.PC))
        instruction = opc.Instruction.fromAddr(self.PC, self)
        print instruction.disassemble()

    def interrupt(self, vector):
        # much like the BRK opcode, but we don't set the B flag, and
        # the new address is determined by the passed interrupt
        # vector. In theory there's some "interrupt highjacking"
        # behavior to emulate but I don't think I care.
        pcHigh = self.PC >> 8
        pcLow = self.PC & 0xff
        self.stackPush(pcHigh)
        self.stackPush(pcLow)
        self.stackPush(self.flags)
        self.setFlag(FLAG_I, True)
        self.PC = self.mem.dereference(vector)

    def cpuTick(self):
        # let's pretend the clock doesn't exist for now
        if self.nmiPending:
            self.interrupt(mem.VEC_NMI)
            self.nmiPending = False
        elif self.irqPending and not self.flag(FLAG_I):
            self.interrupt(mem.VEC_IRQ)
            self.irqPending = False
        # TODO also process RST here (if I feel like it)
        instruction = opc.Instruction.fromAddr(self.PC, self)
        self.PC = instruction.nextaddr
        instruction.call(self)
        # self.printState()

    def tick(self):
        self.ppu.ppuTick()
        self.cpuTick()
