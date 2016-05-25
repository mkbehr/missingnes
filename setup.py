# set up things to link screenmodule
# TODO set up cflags here too I guess
from distutils.core import setup, Extension

module1 = Extension('cscreen',
                    sources = ['screenmodule.cpp'])

setup (name = 'screentest',
       version = '0.1',
       description = 'Testing distutils for linking to c functions',
       ext_modules = [module1])
