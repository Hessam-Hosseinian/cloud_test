#!/usr/bin/env python3
import csv
import json
import sys


for line in sys.stdin:
    row = next(csv.reader([line]))
    if not row or row[0] == "timestamp" or len(row) < 10:
        continue
    try:
        status = int(row[7])
        elapsed = float(row[8])
    except ValueError:
        continue

    successful = int(200 <= status < 400)
    client_error = int(400 <= status < 500)
    server_error = int(500 <= status < 600)
    metrics = [1, successful, client_error, server_error, elapsed]
    endpoint = row[6].split("?", 1)[0]
    dimensions = [
        ("service", row[4]),
        ("endpoint", endpoint),
        ("scenario", row[3]),
    ]
    for dimension, value in dimensions:
        print(json.dumps([dimension, value], separators=(",", ":")) + "\t" +
              json.dumps(metrics, separators=(",", ":")))
