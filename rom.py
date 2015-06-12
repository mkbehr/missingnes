import sys

class NESRom(object):
    """An iNES format ROM file. (Does not support NES 2.0 features.)"""

    def __init__(self, prgrom, chrrom, mapper):
        # TODO flags
        
        # TODO: think about what format to store our ROMs in
        # (currently they're bytestrings, which can be passed to
        # struct but need to use ord to compare them otherwise)
        self.prgrom = prgrom
        self.chrrom = chrrom
        self.mapper = mapper

    @staticmethod
    def fromByteString(bytes):
        # See documentation at http://wiki.nesdev.com/w/index.php/INES

        def fail(s):
            raise RuntimeError(s)
        def notimp(s):
            raise NotImplementedError(s)

        index = 0

        # The first 16 bytes are the header.
        header = bytes[0:16]

        index += 16

        if header[0:4] != "NES\x1A":
            fail("Magic number failed")

        prgromsize = ord(header[4]) * (2**14) # 16KB
        print "PRG ROM size: %d" % prgromsize

        chrromsize = ord(header[5]) * (2**13) # 8KB
        if chrromsize:
            print "CHR ROM size: %d" % chrromsize
        else:
            print "CHR RAM"
            print >> sys.stderr, ("WARNING: CHR RAM not implemented")

        print "Flags 6 (unimplemented): %s" % format(ord(header[6]), '08b')
        if ord(header[6]) & 2:
            notimp("Can't read ROM file with trainer")
        if ord(header[6]) & 9: # 0b1001
            print >> sys.stderr, "WARNING: vertical mirroring not implemented"
        
        print "Flags 7 (unimplemented): %s" % format(ord(header[7]), '08b')

        mapper = ((ord(header[6]) & 0xf0) / 0x10) + (ord(header[7]) & 0xf0)
        print "Mapper: %d" % mapper
        if mapper != 0 and mapper != 1:
            notimp("Unimplemented mapper %d" % mapper)

        prgram = ord(header[8])
        if prgram == 0:
            prgram = 1
        print "PRG RAM size: %d * 8 KB" % prgram

        print "Flags 9 (unimplemented): %s" % format(ord(header[9]), '08b')
        print "Flags 10 (unimplemented): %s" % format(ord(header[10]), '08b')

        for byte in header[11:]:
            if ord(byte) != 0:
                print "Warning: header not properly zero-filled"

        prgrom = bytes[index:index+prgromsize]
        index += prgromsize

        chrrom = bytes[index:index+chrromsize]
        index += chrromsize

        print "unread bytes: %d" % (len(bytes) - index)

        return NESRom(prgrom = prgrom, chrrom = chrrom, mapper = mapper)
        
def readRom(path):
    with open(path, 'rb') as f:
        return NESRom.fromByteString(f.read())
