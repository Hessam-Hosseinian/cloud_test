#!/usr/bin/env python3
import json
import sys
from collections import Counter


service_stats = []
endpoint_stats = []
entity_totals = {"team": Counter(), "matchday": Counter(), "stadium": Counter()}
popular_team_by_country = {}
metadata = {}


for line in sys.stdin:
    try:
        _key, payload = line.rstrip("\r\n").split("\t", 1)
        record = json.loads(payload)
        tag, row = record["tag"], record["row"]
    except (ValueError, KeyError, json.JSONDecodeError):
        continue
    if tag == "metadata":
        metadata.update(row)
    elif tag == "service" and len(row) >= 7:
        service_stats.append({"name": row[0], "total": int(row[1]),
                              "error_rate": float(row[5]), "avg_time": float(row[6])})
    elif tag == "endpoint" and len(row) >= 7:
        endpoint_stats.append({"name": row[0], "avg_time": float(row[6])})
    elif tag in {"team", "matchday"} and len(row) >= 3:
        entity_totals[tag][row[1]] += int(row[2])
    elif tag == "stadium" and len(row) >= 4 and row[1] == "stadium":
        entity_totals[tag][row[2]] += int(row[3])
    elif tag == "popular_team" and len(row) >= 3:
        popular_team_by_country[row[0]] = row[1]


def max_name(items, metric):
    if not items:
        return None
    return sorted(items, key=lambda item: (-item[metric], item["name"]))[0]["name"]


def counter_max(counter):
    if not counter:
        return None
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]


summary = {
    "total_requests": sum(item["total"] for item in service_stats),
    "most_requested_service": max_name(service_stats, "total"),
    "highest_error_rate_service": max_name(service_stats, "error_rate"),
    "slowest_endpoint": max_name(endpoint_stats, "avg_time"),
    "most_popular_team_overall": counter_max(entity_totals["team"]),
    "most_requested_match_day_overall": counter_max(entity_totals["matchday"]),
    "most_requested_stadium_overall": counter_max(entity_totals["stadium"]),
    "popular_team_by_country": dict(sorted(popular_team_by_country.items())),
    "predicted_champion": metadata.get("predicted_champion"),
    "predicted_final": metadata.get("predicted_final"),
    "predicted_final_winner": metadata.get("predicted_final_winner"),
    "predicted_final_stadium": metadata.get("predicted_final_stadium"),
}
print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
