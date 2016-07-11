import functools

# Note: this approach to cheats does cause a small speed hit. It might
# be faster to directly interact with the array we use to store
# physical memory and intercept reads/writes there.

class CheatManager(object):

    def __init__(self, cheats):
        self.cheats = cheats

    def readDecorator(self, readMethod):
        out = readMethod
        for cheat in self.cheats:
            out = cheat.readDecorator(out)
        return out

    def writeDecorator(self, writeMethod):
        out = writeMethod
        for cheat in self.cheats:
            out = cheat.writeDecorator(out)
        return out

    def wrapMemory(self, memory):
        memory.read = self.readDecorator(memory.read)
        memory.write = self.writeDecorator(memory.write)

class Cheat(object):

    def __init__(self, readDecorator = None, writeDecorator = None):
        self._readDecorator = readDecorator
        self._writeDecorator = writeDecorator

    def readDecorator(self, readMethod):
        if self._readDecorator:
            return self._readDecorator(readMethod)
        else:
            return readMethod

        # def wrappedRead(memory, address):
        #     return memory.readMethod(address)
        # return functools.update_wrapper(wrappedRead, readMethod)

    def writeDecorator(self, writeMethod):
        if self._writeDecorator:
            return self._writeDecorator(writeMethod)
        else:
            return writeMethod

    @staticmethod
    def freezeRead(frozenAddress, value):
        if isinstance(value, int):
            value = chr(value)
        def freezeReadDecorator(readMethod):
            def wrappedRead(address):
                if address == frozenAddress:
                    return value
                else:
                    return readMethod(address)
            return functools.update_wrapper(wrappedRead, readMethod)
        return Cheat(readDecorator = freezeReadDecorator)

    # possibly not necessary, but may as well
    @staticmethod
    def freezeWrite(frozenAddress, frozenValue):
        def freezeWriteDecorator(writeMethod):
            def wrappedWrite(address, val):
                if address == frozenAddress:
                    return writeMethod(address, frozenValue)
                else:
                    return writeMethod(address, val)
            return functools.update_wrapper(wrappedWrite, writeMethod)
        return Cheat(writeDecorator = freezeWriteDecorator)


smbInvincible = Cheat.freezeRead(0x079f, 1)

smbInfiniteLives = Cheat.freezeRead(0x75a, 1)

def smbNoFallWriteDecorator(writeMethod):
    # We need to talk to the memory object here, so writeMethod needs
    # to be a bound method of that memory object.
    assert(writeMethod.__self__)
    memory = writeMethod.__self__
    def wrappedWrite(address, val):
        if isinstance(val, int): # someday we will want to get rid of this chr/ord weirdness
            val = chr(val)
        if ((address == 0x00ce) # mario's Y pos on screen
            and ord(val) > 180 # too low
            and (ord(memory.read(0x000e)) != 0x0b) # mario isn't dying
            and (ord(memory.read(0x00b5)) == 1) # mario is on screen
        ):
            val = chr(20) # warp mario to top of screen
            return writeMethod(address, val)
            # Also tried keeping mario at y=180 and writing 0 to 0x1d.
            # In theory, that makes mario able to jump again. In
            # practice, doesn't seem to work.
        else:
            return writeMethod(address, val)
    return functools.update_wrapper(wrappedWrite, writeMethod)

smbNoFall = Cheat(writeDecorator = smbNoFallWriteDecorator)
