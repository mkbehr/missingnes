import cheats
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
    parser.add_argument("--ppu-debug",
                        help="Print PPU debug information",
                        dest="ppuDebug",
                        action="store_true")
    # TODO: more general cheat interface
    parser.add_argument("--smb-cheats",
                        help="Activate cheats for Super Mario Bros.",
                        dest="smbCheats",
                        action="store_true")
    args = parser.parse_args()
    return args

def makeCPU(romfilepath,
            *cpuargs, **cpukwargs):
    r = rom.readRom(romfilepath)
    return cpu.CPU(rom=r,
                   *cpuargs, **cpukwargs)

def run(c):
    while True:
        c.tick()

if __name__ == "__main__":
    args = getargs()
    if args.smbCheats:
        chts = cheats.CheatManager([cheats.smbInvincible,
                                    cheats.smbInfiniteLives,
                                    cheats.smbNoFall])
    else:
        chts = None
    c = makeCPU(args.rom,
                audioEnabled = args.audio,
                ppuDebug = args.ppuDebug,
                cheats = chts)
    run(c)
