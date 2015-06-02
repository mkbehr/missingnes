import cpu
import mem
import opc
import rom

ROMFILE = 'nestest.nes'

nestestrom = rom.readRom(ROMFILE)
c = cpu.CPU(prgrom = nestestrom.prgrom, chrrom = nestestrom.chrrom)
startaddr = mem.dereference(mem.VEC_RST, c)
startop = opc.Operation.fromAddr(startaddr, c)
