class SpriteRow(object):
    """An object representing the portion of a sprite displayed on a
single scanline.

    """

    def __init__(self, x, lowcolor, highcolor, palette, horizontalMirror, priority):
        # TODO sprite attributes (byte 2)
        self.x = x
        self.lowcolor = lowcolor
        self.highcolor = highcolor
        self.palette = palette # index into the palette RAM's sprite section: 0-3
        self.horizontalMirror = horizontalMirror
        self.priority = priority
