import cpu
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

ROMFILE = 'donkeykong.nes'
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

def showscreen():
    import numpy as np
    from matplotlib import pyplot as plt
    img = 3 - np.array(c.ppu.screen).T
    fig = plt.imshow(img, interpolation='nearest', cmap='Greys')
    plt.axis('off')
    fig.axes.get_xaxis().set_visible(False)
    fig.axes.get_yaxis().set_visible(False)
    plt.savefig('screen.png', bbox_inches='tight', pad_inches = 0)
    plt.show()

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

if __name__ == "__main__":
    run()        
