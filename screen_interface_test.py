import libscreen
screen = libscreen.Screen()
drawval = 0
while (drawval == 0):
    screen.drawToBuffer()
    drawval = screen.draw()
