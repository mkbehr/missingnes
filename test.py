import cpu
import instruction
import mem
import opc
import rom

import time

# ROMFILE = 'nestest.nes'
# STARTADDR = 0xC000

# ROMFILE = 'instr_test-v4/official_only.nes'
# # unfortunately, the rom singles use unofficial instructions
# ROMFILE = 'instr_test-v4/rom_singles/02-implied.nes'
# STARTADDR = None

# ROMFILE = 'donkeykong.nes'
# STARTADDR = None

ROMFILE = 'smb.nes'
STARTADDR = None

nestestrom = rom.readRom(ROMFILE)
c = cpu.CPU(rom=nestestrom)
startaddr = c.mem.dereference(mem.VEC_RST)
startop = opc.instrFromAddr(startaddr, c)
firstops = opc.instrListFromAddr(startaddr, 50, c)
firstassem = "\n".join([op.disassemble() for op in firstops])

if STARTADDR is not None:
    c.PC = STARTADDR
c.printState()

def run(delay=0):
    instructions = 0
    try:
        while True:
            c.tick()
            instructions += 1
            time.sleep(delay)
    finally:
        print "Executed %d instructions." % instructions

def runCpu(delay=0):
    instructions = 0
    try:
        while True:
            c.cpuTick()
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

def runUntilFrame(frame):
    instructions = 0
    while c.ppu.frame < frame:
        c.tick()
        instructions += 1
    print "Executed %d instructions." % instructions

def instrTest():
    while c.mem.prgram[0] != '\x80':
        # ignore GPU for now to run faster
        c.cpuTick()
    print "running tests"
    while c.mem.prgram[0] == '\x80':
        c.cpuTick()
    print itMessage()

def itMessage():
    start = 4
    end = c.mem.prgram[start:].index('\x00') + start
    return ''.join(c.mem.prgram[start:end])

def step():
    c.tick()
    c.printState()

def reset():
    global c
    c.ppu.pgscreen.window.close() # still doesn't seem to work
    c = cpu.CPU(rom=nestestrom)
    if STARTADDR is not None:
        c.PC = STARTADDR
    c.printState()

if __name__ == "__main__":
    run()
