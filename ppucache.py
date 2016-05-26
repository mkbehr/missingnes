import palette

class PPUCache(object):
    """Caches images to be used by the PPU."""

    def __init__(self, ppu):
        self.ptabCache = {}
        self.bgTileCache = {}
        self.spriteCache = {}
        self.ppu = ppu
        self.mem = ppu.cpu.mem

    def ptabTile(self, base, tile):
        """Get the tile from the specified pattern table entry as a byte
        array. Caches results, assuming that pattern tables are stored
        in ROM and never remapped.

        Args:
            base: 0 or 1, corresponding to the relevant PPUCTRL bit.
            tile: A byte specifying the tile, corresponding to the
                  nametable entry.
        Returns:
            The PIL palette-mode image for the tile.

        """
        cacheIndex = tile + (base << 8)
        if cacheIndex not in self.ptabCache:
            self.ptabCache[cacheIndex] = self._fetchPtabTile(base, tile)
        return self.ptabCache[cacheIndex]

    def _fetchPtabTile(self, base, tile):
        # finding pattern table entry:
        #
        # bits 0 through 2 are the "fine y offset", the y position
        # within a tile (y position % 8, I guess)
        #
        # bit 3 is the bitplane: we'll need to read once with it
        # set and once with it unset to get two bits of color
        #
        # bits 4 through 7 are the column of the tile (column / 8)
        #
        # bits 8 through b are the tile row (row / 8)
        #
        # bit c is the same as self.bgPatternTableAddr
        #
        # bits d through f are 0 (pattern tables go from 0000 to 1fff)

        entryStart = (
            (0    << 0 ) + # 0-2: fine y offset
            (0    << 3 ) + # 3: dataplane
            (tile << 4 ) + # 4-11: column and row
            (base << 12)) # 12: pattern table base
        # bits d through f are 0 (pattern tables go from 0000 to 1fff)

        contents = bytearray(64)
        for finey in range(8):
            lowplane = entryStart | finey
            highplane = lowplane | 8
            lowbyte = ord(self.mem.ppuRead(lowplane))
            highbyte = ord(self.mem.ppuRead(highplane))
            for finex in range(8):
                # most significant bit is leftmost bit
                finexbit = 7 - finex

                pixelbit0 = (lowbyte >> finexbit) & 0x1
                pixelbit1 = (highbyte >> finexbit) & 0x1
                colorindex = pixelbit0 + pixelbit1 * 2

                # TODO decide where to handle grayscale
                # if self.grayscale:
                #     colorindex &= 0x30

                contents[finex + finey * 8] = colorindex # TODO confirm contents index

        return contents

    def bgTile(self, base, tile, bg, paletteData):
        """Get the specified tile as a byte string, given palette data."""
        # TODO bg is probably not a relevant argument anymore
        cacheIndex = (base, tile, bg, paletteData[0], paletteData[1], paletteData[2])
        if cacheIndex not in self.bgTileCache:
            self.bgTileCache[cacheIndex] = self._pglFetchBgTile(base, tile, bg, paletteData)
        return self.bgTileCache[cacheIndex]

    def _pglFetchBgTile(self, base, tile, bg, paletteData):
        indexedTileContents = self.ptabTile(base, tile)
        palettebytes = palette.smallPaletteBytes(bg, paletteData)

        img_bytes = bytearray(8*8*4)
        for (i, colorIndex) in enumerate(indexedTileContents):
            if colorIndex == 0:
                img_bytes[i*4 : (i+1)*4] = '\x00\x00\x00\x00' # transparent
            else:
                img_bytes[i*4 : (i+1)*4] = palette.RGBA_PALETTE_BYTEENTRIES[paletteData[colorIndex-1]]

        return str(img_bytes)

    def spriteTexture(self, base, tile, flipH, flipV, paletteData):
        """Get the specified sprite as a byte string to be used in a texture."""
        # FIXME the name is kind of inaccurate now
        cacheIndex = (base, tile, flipH, flipV, paletteData[0], paletteData[1], paletteData[2])
        if cacheIndex not in self.spriteCache:
            self.spriteCache[cacheIndex] = self._fetchSpriteTexture(base, tile, flipH, flipV, paletteData)
        return self.spriteCache[cacheIndex]

    def _fetchSpriteTexture(self, base, tile, flipH, flipV, paletteData):
        indexedSpriteContents = self.ptabTile(base, tile)

        # TODO this palette-application code should probably just go in palette.py

        xIndices = range(8)
        if flipH:
            xIndices.reverse()
        yIndices = range(8)
        if flipV:
            yIndices.reverse()

        img_bytes = bytearray(8*8*4)
        i = 0
        for y in yIndices:
            for x in xIndices:
                colorIndex = indexedSpriteContents[x + y*8]
                if colorIndex == 0:
                    img_bytes[i*4 : (i+1)*4] = '\x00\x00\x00\x00' # transparent
                else:
                    img_bytes[i*4 : (i+1)*4] = palette.RGBA_PALETTE_BYTEENTRIES[paletteData[colorIndex-1]]
                i += 1

        return str(img_bytes)
