class SpriteRow(object):
    """An object representing the portion of a sprite displayed on a
single scanline.

    """

    def __init__(self, index, x, lowcolor, highcolor, palette, horizontalMirror, priority):
        self.index = index
        self.x = x
        self.lowcolor = lowcolor
        self.highcolor = highcolor
        self.palette = palette # index into the palette RAM's sprite section: 0-3
        self.horizontalMirror = horizontalMirror
        self.priority = priority
