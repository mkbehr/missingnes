import cpu
import mem
import opc
import rom

import time

ROMFILE = 'nestest.nes'

nestestrom = rom.readRom(ROMFILE)
c = cpu.CPU(prgrom = nestestrom.prgrom, chrrom = nestestrom.chrrom)
startaddr = c.mem.dereference(mem.VEC_RST)
startop = opc.Instruction.fromAddr(startaddr, c)
firstops = opc.Instruction.listFromAddr(startaddr, 50, c)
firstassem = "\n".join([op.disassemble() for op in firstops])

c.PC = 0xC000
c.printState()

def run(delay=0.05):
    instructions = 0
    try:
        while True:
            c.tick()
            instructions += 1
            time.sleep(delay)
    finally:
        print "Executed %d instructions." % instructions

if __name__ == "__main__":
    run()        
