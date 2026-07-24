#!/usr/bin/env python3
"""Copy log lines into new atomic JSONL files for Spark file streaming."""

import argparse
import time
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True,
                        help="source JSONL file; repeat for multiple files")
    parser.add_argument("--output", required=True)
    parser.add_argument("--prefix", default="batch")
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--max-lines", type=int, default=0)
    parser.add_argument("--delay", type=float, default=0.0)
    return parser.parse_args()


def batches(sources, batch_size, max_lines):
    batch = []
    emitted = 0
    for source_name in sources:
        with open(source_name, encoding="utf-8") as source:
            for line in source:
                if max_lines and emitted + len(batch) >= max_lines:
                    if batch:
                        yield batch
                    return
                if line.strip():
                    batch.append(line)
                if len(batch) == batch_size:
                    yield batch
                    emitted += len(batch)
                    batch = []
    if batch:
        yield batch


def main():
    args = parse_args()
    if args.batch_size < 1 or args.max_lines < 0:
        raise SystemExit("batch size must be positive and max lines non-negative")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    file_count = 0
    line_count = 0
    for file_count, lines in enumerate(
            batches(args.source, args.batch_size, args.max_lines), 1):
        temporary = output / (".{0}_{1:06d}.tmp".format(args.prefix, file_count))
        destination = output / ("{0}_{1:06d}.jsonl".format(args.prefix, file_count))
        with temporary.open("w", encoding="utf-8") as target:
            target.writelines(lines)
        temporary.replace(destination)
        line_count += len(lines)
        print("created {} ({} lines)".format(destination, len(lines)))
        if args.delay:
            time.sleep(args.delay)
    print("exported {} lines in {} new files".format(line_count, file_count))


if __name__ == "__main__":
    main()
