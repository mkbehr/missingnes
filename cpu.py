import mem
import opc

FLAG_C = 0x1 # carry
FLAG_Z = 0x2 # zero result
FLAG_I = 0x4 # interrupt disable
FLAG_D = 0x8 # decimal mode
FLAG_B = 0x10 # break command
FLAG_EXP = 0x20 # expansion
FLAG_V = 0x40 # overflow
FLAV_N = 0x80 # negative result

class CPU(object):

    def __init__(self, prgrom, chrrom):
        """Sets up an initial CPU state loading from the given ROM. Simulates
        the reset signal."""
        # see http://wiki.nesdev.com/w/index.php/CPU_power_up_state
        # for some initial values
        self.prgrom = prgrom
        self.prgromsize = len(prgrom)
        self.chrrom = chrrom
        self.chrromsize = len(chrrom)

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

        # Now that everything is set up, simulate the RST signal.
        # If we ever track frames, this will affect those.
        self.PC = mem.dereference(mem.VEC_RST, self)

    def flag(self, mask):
        return self.flags & mask

    def setFlag(self, mask, val): # val should be boolean
        if val:
            self.flags |= mask
        else:
            self.flags &= (0xFF ^ mask)


    # do stack pushing and popping actually want to live in the CPU?
    def stackPush(self, val):
        raise NotImplementedError()

    def stackPop(self):
        raise NotImplementedError()

    def printState(self):
        print ("A = %02x X = %02x Y = %02x flags = %02x PC = %04x" %
               (self.reg_A, self.reg_X, self.reg_Y, self.flags, self.PC))
        instruction = opc.Instruction.fromAddr(self.PC, self)
        print instruction.disassemble()

    def tick(self):
        # let's pretend the clock doesn't exist for now
        instruction = opc.Instruction.fromAddr(self.PC, self)
        self.PC = instruction.nextaddr
        instruction.call(self)
        self.printState()
