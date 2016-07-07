import cpu
import instruction
import mem
import opc
import rom

import argparse
import time

def getargs():
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", help="Path to the ROM to run")
    parser.add_argument("--no-audio",
                        help="Disable audio output",
                        dest="audio",
                        action="store_false")
    args = parser.parse_args()
    print args.rom
    return args

def makeCPU(romfilepath,
            *cpuargs, **cpukwargs):
    r = rom.readRom(romfilepath)
    return cpu.CPU(prgrom = r.prgrom,
                   chrrom = r.chrrom,
                   mapper = r.mapper,
                   *cpuargs, **cpukwargs)

def run(c):
    while True:
        c.tick()

if __name__ == "__main__":
    args = getargs()
    print args
    c = makeCPU(args.rom,
                audioEnabled = args.audio)
    run(c)
