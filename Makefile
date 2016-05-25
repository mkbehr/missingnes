SHELL=/bin/bash
CXX=g++
CPPFLAGS=-g $(shell pkg-config --cflags glfw3)
LDFLAGS=$(shell pkg-config --static --libs glfw3) -framework Python

all: cscreen.so

screen: screen.o
	$(CXX) $(LDFLAGS) -o screen screen.o

screen.o: screen.cpp screen.h

cscreen.so: screen.cpp screen.h screen.o screenmodule.cpp setup.py
	CPPFLAGS="$(CPPFLAGS)" LDFLAGS="$(LDFLAGS)" CXX="$(CXX)" /usr/bin/python setup.py build_ext --inplace --force

# glfw-test:
# 	g++ `pkg-config --cflags glfw3` `pkg-config --static --libs glfw3` glfw-test.cpp -o glfw-test -g

# screen: screen.cpp screen.h
# 	g++ `pkg-config --cflags glfw3` `pkg-config --static --libs glfw3` screen.cpp -o screen -g
