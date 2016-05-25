// this might be mac-specific
#include <Python/Python.h>
// #include "screen.h"

// this seems like a hack - is this really how python wants me to do this?
#include "screen.cpp"

static Screen *sc;

static PyObject *screenInit(PyObject *self, PyObject *args) {
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  sc = (Screen *) malloc(sizeof(Screen));
  *sc = Screen();
  Py_RETURN_NONE;
}

static PyObject *screenDrawToBuffer(PyObject *self, PyObject *args) {
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  sc->drawToBuffer();
  Py_RETURN_NONE;
}

static PyObject *screenDraw(PyObject *self, PyObject *args) {
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  int out = sc->draw();
  return Py_BuildValue("i", out);
  Py_RETURN_NONE;
}


static PyMethodDef ScreenMethods[] = {
  {"init", screenInit, METH_VARARGS, "Create a screen object."},
  {"drawToBuffer", screenDrawToBuffer, METH_VARARGS, "Render state to internal buffer."},
  {"draw", screenDraw, METH_VARARGS, "Draw internal buffer to screen."},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initcscreen(void)
{
  (void) Py_InitModule("cscreen", ScreenMethods);
}
