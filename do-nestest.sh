#!/bin/sh
python test.py | egrep "^[0-9a-f]{4}" | cut -c 1-4 > testpcs
