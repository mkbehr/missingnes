class CPU(object):

    def __init__(self, prgrom, chrrom): # TODO more
        self.prgrom = prgrom
        self.prgromsize = len(prgrom)
        self.chrrom = chrrom
        self.chrromsize = len(chrrom)
