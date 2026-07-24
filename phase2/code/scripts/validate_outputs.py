#!/usr/bin/env python3
import csv
import json
import os
from pathlib import Path


REQUIRED = {
    "outputs/job1/cleaned_nginx_logs.csv": 10,
    "outputs/job1/cleaned_service_logs.csv": 10,
    "outputs/job1/invalid_logs.csv": 3,
    "outputs/job2/service_stats.csv": 7,
    "outputs/job2/endpoint_stats.csv": 7,
    "outputs/job2/scenario_stats.csv": 7,
    "outputs/job3/country_team_requests.csv": 3,
    "outputs/job3/country_matchday_requests.csv": 3,
    "outputs/job3/country_stadium_requests.csv": 4,
    "outputs/job4/popular_team_by_country.csv": 3,
    "outputs/job4/popular_matchday_by_country.csv": 3,
    "outputs/job4/popular_stadium_by_country.csv": 4,
}


for filename, expected_columns in REQUIRED.items():
    path = Path(filename)
    if not path.is_file():
        raise SystemExit("missing output: {}".format(filename))
    with path.open(newline="", encoding="utf-8") as handle:
        rows = csv.reader(handle)
        header = next(rows, None)
        if header is None or len(header) != expected_columns:
            raise SystemExit("invalid header/schema: {}".format(filename))
        for row_number, row in enumerate(rows, 2):
            if len(row) != expected_columns:
                raise SystemExit(
                    "invalid row {} in {}".format(row_number, filename)
                )

summary_path = Path("outputs/final/summary.json")
with summary_path.open(encoding="utf-8") as handle:
    summary = json.load(handle)
required_summary_keys = {
    "total_requests", "most_requested_service", "highest_error_rate_service",
    "slowest_endpoint", "most_popular_team_overall",
    "most_requested_match_day_overall", "most_requested_stadium_overall",
    "popular_team_by_country", "predicted_champion", "predicted_final",
    "predicted_final_winner", "predicted_final_stadium",
}
missing = required_summary_keys - summary.keys()
if missing:
    raise SystemExit("summary.json misses keys: " + ", ".join(sorted(missing)))
expected_requests = os.environ.get("EXPECTED_REQUESTS")
if expected_requests is not None:
    actual_requests = int(summary["total_requests"])
    if actual_requests != int(expected_requests):
        raise SystemExit(
            "total_requests is {}, expected {}".format(
                actual_requests, expected_requests
            )
        )
print("Validated {} required output files.".format(len(REQUIRED) + 1))
