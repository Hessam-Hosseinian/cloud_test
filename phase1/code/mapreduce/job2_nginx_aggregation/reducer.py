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
totals = [0, 0, 0, 0, 0.0]


def emit(key, values):
    if key is None:
        return
    dimension, name = json.loads(key)
    total, successful, client_errors, server_errors, elapsed_sum = values
    error_rate = ((client_errors + server_errors) * 100.0 / total) if total else 0.0
    avg_time = elapsed_sum / total if total else 0.0
    row = [name, total, successful, client_errors, server_errors,
           "{:.4f}".format(error_rate), "{:.3f}".format(avg_time)]
    print(dimension + "\t" + csv_line(row))


for line in sys.stdin:
    try:
        key, payload = line.rstrip("\r\n").split("\t", 1)
        values = json.loads(payload)
    except (ValueError, json.JSONDecodeError):
        continue
    if current_key is not None and key != current_key:
        emit(current_key, totals)
        totals = [0, 0, 0, 0, 0.0]
    current_key = key
    for index in range(4):
        totals[index] += int(values[index])
    totals[4] += float(values[4])

emit(current_key, totals)
