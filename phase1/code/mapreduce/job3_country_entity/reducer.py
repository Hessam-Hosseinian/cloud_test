#!/usr/bin/env python3
import csv
import io
import json
import sys


def csv_line(values):
    output = io.StringIO()
    csv.writer(output, lineterminator="").writerow(values)
    return output.getvalue()


current_key = None
count = 0


def emit(key, total):
    if key is None:
        return
    category, country, entity_type, entity_value = json.loads(key)
    if category == "stadium":
        row = [country, entity_type, entity_value, total]
    else:
        row = [country, entity_value, total]
    print(category + "\t" + csv_line(row))


for line in sys.stdin:
    try:
        key, value = line.rstrip("\r\n").split("\t", 1)
        value = int(value)
    except ValueError:
        continue
    if current_key is not None and key != current_key:
        emit(current_key, count)
        count = 0
    current_key = key
    count += value

emit(current_key, count)
