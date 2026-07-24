#!/usr/bin/env python3
import csv
import hashlib
import io
import json
import sys


NGINX_FIELDS = [
    "timestamp", "request_id", "client_country", "scenario", "service",
    "method", "path", "status_code", "request_time_sec", "user_agent",
]
SERVICE_FIELDS = [
    "timestamp", "request_id", "client_country", "service", "endpoint",
    "entity_type", "entity_value", "status_code", "processing_time_ms",
    "event_type",
]


def csv_line(values):
    output = io.StringIO()
    csv.writer(output, lineterminator="").writerow(values)
    return output.getvalue()


def invalid(source, error, raw):
    digest = hashlib.sha256(
        "{}\0{}\0{}".format(source, error, raw).encode("utf-8")
    ).hexdigest()
    print("invalid:{}\t{}".format(digest, csv_line([source, error, raw])))


def keyed_record(source, request_id, values):
    """Use a stable key so the reducer can remove network-retry duplicates."""
    digest = hashlib.sha256(str(request_id).encode("utf-8")).hexdigest()
    print("{}:{}\t{}".format(source, digest, csv_line(values)))


for raw_line in sys.stdin:
    raw = raw_line.rstrip("\r\n")
    if not raw:
        continue
    try:
        record = json.loads(raw)
        if not isinstance(record, dict):
            raise ValueError("JSON value is not an object")
    except (json.JSONDecodeError, ValueError) as exc:
        invalid("unknown", "invalid_json: {}".format(exc), raw)
        continue

    source = "nginx" if "request_time_sec" in record else "service"
    required = NGINX_FIELDS if source == "nginx" else SERVICE_FIELDS
    missing = [field for field in required if field not in record]
    if missing:
        invalid(source, "missing_fields: " + ",".join(missing), raw)
        continue

    try:
        status_code = int(record["status_code"])
        if not 100 <= status_code <= 599:
            raise ValueError("status_code is outside HTTP range")
        time_field = "request_time_sec" if source == "nginx" else "processing_time_ms"
        elapsed = float(record[time_field])
        if elapsed < 0:
            raise ValueError("{} is negative".format(time_field))
    except (TypeError, ValueError) as exc:
        invalid(source, "invalid_numeric_field: {}".format(exc), raw)
        continue

    if source == "nginx":
        values = [
            record["timestamp"], record["request_id"], record["client_country"],
            record["scenario"], record["service"], record["method"],
            record["path"], status_code, round(elapsed * 1000, 3),
            record["user_agent"],
        ]
        keyed_record("nginx", record["request_id"], values)
    else:
        values = [
            record["timestamp"], record["request_id"], record["client_country"],
            record["service"], record["endpoint"], record["entity_type"],
            record["entity_value"], status_code, round(elapsed, 3),
            record["event_type"],
        ]
        keyed_record("service", record["request_id"], values)
