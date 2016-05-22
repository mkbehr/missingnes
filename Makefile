all: glfw-test screen

glfw-test:
	g++ `pkg-config --cflags glfw3` `pkg-config --static --libs glfw3` glfw-test.cpp -o glfw-test

screen: screen.cpp screen.h
	g++ `pkg-config --cflags glfw3` `pkg-config --static --libs glfw3` screen.cpp -o screen
