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
best = None


def emit(key, selected):
    if key is None or selected is None:
        return
    category, country = json.loads(key)
    entity_type, entity_value, count = selected
    tag = "popular_" + category
    row = [country, entity_type, entity_value, count] if category == "stadium" else [country, entity_value, count]
    print(tag + "\t" + csv_line(row))


for line in sys.stdin:
    try:
        key, payload = line.rstrip("\r\n").split("\t", 1)
        candidate = json.loads(payload)
        candidate[2] = int(candidate[2])
    except (ValueError, json.JSONDecodeError):
        continue
    if current_key is not None and key != current_key:
        emit(current_key, best)
        best = None
    current_key = key
    if best is None or candidate[2] > best[2] or (candidate[2] == best[2] and candidate[1] < best[1]):
        best = candidate

emit(current_key, best)
