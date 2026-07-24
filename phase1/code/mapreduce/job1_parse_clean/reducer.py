#!/usr/bin/env python3
import sys


for line in sys.stdin:
    line = line.rstrip("\r\n")
    if line:
        print(line)
