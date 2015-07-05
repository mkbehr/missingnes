class SpriteRow(object):
    """An object representing the portion of a sprite displayed on a
single scanline.

    """

    def __init__(self, x, lowcolor, highcolor, horizontalMirror, priority):
        # TODO sprite attributes (byte 2)
        self.x = x
        self.lowcolor = lowcolor
        self.highcolor = highcolor
        self.horizontalMirror = horizontalMirror
        self.priority = priority
