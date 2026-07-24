#!/usr/bin/env python3
import argparse
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--tag", required=True)
parser.add_argument("--header", required=True)
args = parser.parse_args()

output_path = Path(args.output)
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(args.input, encoding="utf-8") as source, output_path.open("w", encoding="utf-8") as target:
    target.write(args.header + "\n")
    prefix = args.tag + "\t"
    for line in source:
        if line.startswith(prefix):
            target.write(line[len(prefix):])
