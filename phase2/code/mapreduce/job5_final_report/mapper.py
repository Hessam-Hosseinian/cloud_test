#!/usr/bin/env python3
import csv
import json
import sys


VALID_TAGS = {
    "service", "endpoint", "scenario", "team", "matchday", "stadium",
    "popular_team", "popular_matchday", "popular_stadium",
}


for line in sys.stdin:
    stripped = line.strip()
    if not stripped:
        continue
    if stripped.startswith("{"):
        try:
            metadata = json.loads(stripped)
            print("summary\t" + json.dumps({"tag": "metadata", "row": metadata},
                                              ensure_ascii=False, separators=(",", ":")))
        except json.JSONDecodeError:
            pass
        continue
    try:
        tag, payload = stripped.split("\t", 1)
        if tag not in VALID_TAGS:
            continue
        row = next(csv.reader([payload]))
        print("summary\t" + json.dumps({"tag": tag, "row": row},
                                          ensure_ascii=False, separators=(",", ":")))
    except (ValueError, csv.Error):
        continue
