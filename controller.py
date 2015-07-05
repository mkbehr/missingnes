class Controller(object):
    """A standard NES controller. Only emulates the first controller."""

    def __init__(self):

        self.strobe = False
        self.button = 0
        self.inputState = ControllerButtons()
        self.inputState = ControllerButtons(rightButton = True) # DEBUG

    def inputStrobe(self, strobe):
        self.strobe = strobe
        if strobe:
            self.button = 0

    def read(self):
        out = 0x40
        if self.button > 7:
            out += 1
        else:
            if self.inputState.states[self.button]:
                out += 1
            if not self.strobe:
                self.button += 1
        return out

    def setInputState(inputState):
        self.inputState = inputState

class ControllerButtons(object):
    # Button order is: A, B, Select, Start, Up, Down, Left, Right.

    # There is possibly a better way of encoding this, but oh well.

    def __init__(self,
                 aButton = False, bButton = False,
                 selectButton = False, startButton = False,
                 upButton = False, downButton = False,
                 leftButton = False, rightButton = False):
        self.states = [aButton, bButton, selectButton, startButton,
                       upButton, downButton, leftButton, rightButton]
