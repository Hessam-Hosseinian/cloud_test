#!/usr/bin/env python3
import csv
import json
import sys


for line in sys.stdin:
    row = next(csv.reader([line]))
    if not row or row[0] == "timestamp" or len(row) < 10:
        continue
    country, entity_type, entity_value = row[2], row[5], row[6]
    if not country or not entity_value:
        continue
    if entity_type == "team":
        category = "team"
    elif entity_type == "match_day":
        category = "matchday"
    elif entity_type in {"stadium", "city"}:
        category = "stadium"
    else:
        continue
    key = [category, country, entity_type, entity_value]
    print(json.dumps(key, ensure_ascii=False, separators=(",", ":")) + "\t1")
