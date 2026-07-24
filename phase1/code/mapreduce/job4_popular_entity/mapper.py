#!/usr/bin/env python3
import csv
import json
import sys


for line in sys.stdin:
    try:
        category, payload = line.rstrip("\r\n").split("\t", 1)
        row = next(csv.reader([payload]))
        if category == "stadium":
            country, entity_type, entity_value, count = row
        elif category in {"team", "matchday"}:
            country, entity_value, count = row
            entity_type = category
        else:
            continue
        key = json.dumps([category, country], ensure_ascii=False, separators=(",", ":"))
        value = json.dumps([entity_type, entity_value, int(count)],
                           ensure_ascii=False, separators=(",", ":"))
        print(key + "\t" + value)
    except (ValueError, csv.Error, json.JSONDecodeError):
        continue
