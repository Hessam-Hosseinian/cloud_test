#!/usr/bin/env python3
import sys


previous_key = None
for line in sys.stdin:
    line = line.rstrip("\r\n")
    if not line:
        continue
    try:
        key, payload = line.split("\t", 1)
    except ValueError:
        continue
    if key == previous_key:
        continue
    tag = key.split(":", 1)[0]
    print("{}\t{}".format(tag, payload))
    previous_key = key
