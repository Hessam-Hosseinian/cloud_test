#!/usr/bin/env python3
"""Generate deterministic, resource-bounded traffic through the Nginx gateway."""

import argparse
import http.client
import random
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode, urlsplit


COUNTRIES = ["Iran", "Germany", "Brazil", "Argentina", "Japan", "USA", "Mexico", "Canada"]
FAVOURITE_TEAMS = {
    "Iran": ["Iran", "Argentina", "Germany"],
    "Germany": ["Germany", "Argentina", "France"],
    "Brazil": ["Brazil", "Argentina", "Portugal"],
    "Argentina": ["Argentina", "Brazil", "Spain"],
    "Japan": ["Japan", "Argentina", "South Korea"],
    "USA": ["USA", "Argentina", "Mexico"],
    "Mexico": ["Mexico", "Argentina", "USA"],
    "Canada": ["Canada", "Argentina", "France"],
}
MATCH_DAYS = [
    "2026-06-12", "2026-06-13", "2026-06-14", "2026-06-15",
    "2026-06-18", "2026-06-19", "2026-06-22", "2026-06-25",
    "2026-07-04", "2026-07-10", "2026-07-19",
]
STADIUMS = [
    "New York New Jersey Stadium", "Dallas Stadium", "Mexico City Stadium",
    "Los Angeles Stadium", "Atlanta Stadium", "BC Place Vancouver",
    "Houston Stadium", "Toronto Stadium",
]
CITIES = ["New York New Jersey", "Dallas", "Mexico City", "Los Angeles", "Vancouver", "Toronto"]
STOP_EVENT = threading.Event()


def weighted_choice(rng, values, weights):
    return rng.choices(values, weights=weights, k=1)[0]


def make_request(rng, index):
    country = rng.choice(COUNTRIES)
    scenario = weighted_choice(
        rng,
        ["normal", "popular", "invalid", "server_error", "slow"],
        [91.5, 5.0, 2.0, 1.0, 0.5],
    )
    service = weighted_choice(
        rng,
        ["team-service", "match-service", "stadium-service"],
        [50, 28, 22],
    )

    if service == "team-service":
        path = "/api/teams"
        if scenario == "invalid":
            params = {"name": "Unknown Team"} if rng.random() < 0.7 else {}
        elif scenario == "popular":
            params = {"name": "Argentina"}
        else:
            favourites = FAVOURITE_TEAMS[country]
            params = {"name": weighted_choice(rng, favourites, [65, 25, 10])}
    elif service == "match-service":
        path = "/api/matches"
        if scenario == "invalid":
            params = {"date": rng.choice(["not-a-date", "2026-05-01", "2026/06/25"])}
        else:
            day_weights = [4, 5, 4, 4, 4, 4, 5, 30, 7, 8, 25]
            params = {"date": weighted_choice(rng, MATCH_DAYS, day_weights)}
    else:
        path = "/api/stadiums"
        if scenario == "invalid":
            params = {"name": "Unknown Stadium"} if rng.random() < 0.7 else {}
        elif rng.random() < 0.25:
            params = {"city": weighted_choice(rng, CITIES, [35, 15, 15, 12, 12, 11])}
        else:
            params = {"name": weighted_choice(rng, STADIUMS, [42, 15, 12, 9, 7, 6, 5, 4])}

    query = urlencode(params)
    request_path = path + (("?" + query) if query else "")
    headers = {
        "X-Request-ID": f"req_{index:06d}",
        "X-Client-Country": country,
        "X-Scenario": scenario,
        "User-Agent": "traffic-generator/1.0",
        "Accept": "application/json",
    }
    return service, scenario, request_path, headers


def worker(worker_id, args, parsed_url):
    rng = random.Random(args.seed + worker_id * 1_000_003)
    connection = None
    counters = Counter()
    total_latency_ms = 0.0

    def connect():
        cls = http.client.HTTPSConnection if parsed_url.scheme == "https" else http.client.HTTPConnection
        return cls(parsed_url.hostname, parsed_url.port, timeout=args.timeout)

    for index in range(worker_id + 1, args.requests + 1, args.workers):
        if STOP_EVENT.is_set():
            break
        service, scenario, request_path, headers = make_request(rng, index)
        full_path = (parsed_url.path.rstrip("/") + request_path) or request_path
        started = time.perf_counter()
        for attempt in range(2):
            try:
                if connection is None:
                    connection = connect()
                connection.request("GET", full_path, headers=headers)
                response = connection.getresponse()
                response.read()
                status = response.status
                break
            except (OSError, http.client.HTTPException):
                counters["network_errors"] += 1
                if connection is not None:
                    connection.close()
                connection = None
                status = 0
                if attempt == 1:
                    break
        total_latency_ms += (time.perf_counter() - started) * 1000
        counters["completed"] += 1
        counters[f"service:{service}"] += 1
        counters[f"scenario:{scenario}"] += 1
        counters[f"status:{status // 100}xx" if status else "status:network_error"] += 1

    if connection is not None:
        connection.close()
    return counters, total_latency_ms


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--nginx-url", default="http://localhost:8080")
    parser.add_argument("--workers", type=int, default=16,
                        help="bounded concurrent connections (default: 16)")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--seed", type=int, default=1405)
    args = parser.parse_args()
    if args.requests < 1:
        parser.error("--requests must be positive")
    if not 1 <= args.workers <= 64:
        parser.error("--workers must be between 1 and 64")
    return args


def main():
    args = parse_args()
    parsed_url = urlsplit(args.nginx_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise SystemExit("--nginx-url must be an HTTP(S) URL")

    print(f"Starting {args.requests:,} requests with {args.workers} workers via {args.nginx_url}")
    started = time.perf_counter()
    totals = Counter()
    total_latency_ms = 0.0
    STOP_EVENT.clear()
    executor = ThreadPoolExecutor(max_workers=args.workers)
    try:
        futures = [executor.submit(worker, i, args, parsed_url) for i in range(args.workers)]
        for future in futures:
            counters, latency_ms = future.result()
            totals.update(counters)
            total_latency_ms += latency_ms
    except KeyboardInterrupt:
        print("Interrupted; stopping workers after their current requests...")
        STOP_EVENT.set()
        executor.shutdown(wait=True, cancel_futures=True)
        raise SystemExit(130)
    else:
        executor.shutdown(wait=True)

    elapsed = time.perf_counter() - started
    print(f"Completed: {totals['completed']:,} in {elapsed:.2f}s ({totals['completed'] / elapsed:.1f} req/s)")
    print(f"Mean client latency: {total_latency_ms / totals['completed']:.2f} ms")
    for key in sorted(k for k in totals if k.startswith(("status:", "service:", "scenario:"))):
        print(f"  {key}: {totals[key]:,}")
    if totals["network_errors"]:
        print(f"Network retries/failures: {totals['network_errors']:,}")


if __name__ == "__main__":
    main()
