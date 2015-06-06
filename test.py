import cpu
import mem
import opc
import rom

import time

# ROMFILE = 'nestest.nes'
# STARTADDR = 0xC000

ROMFILE = 'instr_test-v4/official_only.nes'
STARTADDR = None

nestestrom = rom.readRom(ROMFILE)
c = cpu.CPU(prgrom = nestestrom.prgrom,
            chrrom = nestestrom.chrrom,
            mapper = nestestrom.mapper)
startaddr = c.mem.dereference(mem.VEC_RST)
startop = opc.Instruction.fromAddr(startaddr, c)
firstops = opc.Instruction.listFromAddr(startaddr, 50, c)
firstassem = "\n".join([op.disassemble() for op in firstops])

if STARTADDR is not None:
    c.PC = STARTADDR
c.printState()

def run(delay=0.0001):
    instructions = 0
    try:
        while True:
            c.tick()
            instructions += 1
            time.sleep(delay)
    finally:
        print "Executed %d instructions." % instructions

def runUntil(address):
    instructions = 0
    try:
        while c.PC != address:
            c.tick()
            instructions += 1
    finally:
        print "Executed %d instructions." % instructions

if __name__ == "__main__":
    run()        
