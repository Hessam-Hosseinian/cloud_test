#!/usr/bin/env python3
"""Build a static dashboard from the validated MapReduce summary."""

import argparse
import csv
import html
import json
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--service-stats", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def read_json(path):
    with Path(path).open(encoding="utf-8") as source:
        return json.load(source)


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def esc(value):
    return html.escape(str(value))


def service_rows(rows):
    rendered = []
    for row in rows:
        rendered.append(
            "<tr><td>{}</td><td>{:,}</td><td>{}</td><td>{}</td></tr>".format(
                esc(row["name"]),
                int(row["total_requests"]),
                esc(row["error_rate_percent"]) + "%",
                esc(row["avg_response_time_ms"]) + " ms",
            )
        )
    return "\n".join(rendered)


def country_cards(popular):
    return "\n".join(
        '<div class="country"><span>{}</span><strong>{}</strong></div>'.format(
            esc(country), esc(team)
        )
        for country, team in sorted(popular.items())
    )


def build_page(summary, services):
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>World Cup Log Analytics</title>
  <style>
    :root {{ color-scheme: dark; --bg:#07111f; --panel:#102238; --line:#24445f;
            --cyan:#36d7c7; --gold:#f5c451; --text:#edf7ff; --muted:#93aabe; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter,system-ui,sans-serif; background:
      radial-gradient(circle at 85% 0,#163c54 0,transparent 38%),var(--bg);
      color:var(--text); }}
    main {{ width:min(1100px,92vw); margin:0 auto; padding:48px 0 70px; }}
    header {{ display:flex; justify-content:space-between; gap:20px; align-items:end;
      border-bottom:1px solid var(--line); padding-bottom:24px; }}
    h1 {{ margin:0; font-size:clamp(30px,5vw,55px); letter-spacing:-2px; }}
    .eyebrow {{ color:var(--cyan); font-weight:700; text-transform:uppercase;
      letter-spacing:2px; font-size:12px; }}
    .run {{ color:var(--muted); text-align:right; }}
    .metrics {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px;
      margin:28px 0; }}
    .card,.panel {{ background:linear-gradient(145deg,#142b43,#0d1d31);
      border:1px solid var(--line); border-radius:16px; padding:22px;
      box-shadow:0 16px 40px #02081166; }}
    .card span {{ color:var(--muted); display:block; font-size:13px; }}
    .card strong {{ display:block; margin-top:10px; font-size:24px; color:var(--gold); }}
    .grid {{ display:grid; grid-template-columns:1.25fr .75fr; gap:18px; }}
    h2 {{ margin:0 0 18px; font-size:20px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ padding:12px 8px; text-align:left; border-bottom:1px solid var(--line); }}
    th {{ color:var(--muted); font-size:12px; text-transform:uppercase; }}
    .countries {{ display:grid; grid-template-columns:repeat(2,1fr); gap:9px; }}
    .country {{ padding:11px; border:1px solid var(--line); border-radius:10px; }}
    .country span {{ display:block; color:var(--muted); font-size:12px; }}
    .country strong {{ color:var(--cyan); }}
    footer {{ color:var(--muted); margin-top:25px; font-size:13px; }}
    @media(max-width:800px) {{ .metrics,.grid {{ grid-template-columns:1fr 1fr; }}
      .grid {{ grid-template-columns:1fr; }} }}
    @media(max-width:520px) {{ .metrics,.countries {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body><main>
  <header><div><div class="eyebrow">Cloud Computing · Phase 2</div>
    <h1>World Cup log analytics</h1></div>
    <div class="run">Kubernetes deployment<br>GitLab CI/CD output</div></header>
  <section class="metrics">
    <div class="card"><span>Total requests</span><strong>{total:,}</strong></div>
    <div class="card"><span>Busiest service</span><strong>{service}</strong></div>
    <div class="card"><span>Slowest endpoint</span><strong>{endpoint}</strong></div>
    <div class="card"><span>Predicted champion</span><strong>{champion}</strong></div>
  </section>
  <section class="grid">
    <div class="panel"><h2>Service health from gateway logs</h2>
      <table><thead><tr><th>Service</th><th>Requests</th><th>Error rate</th>
      <th>Average response</th></tr></thead><tbody>{rows}</tbody></table></div>
    <div class="panel"><h2>Popular team by country</h2>
      <div class="countries">{countries}</div></div>
  </section>
  <footer>Generated from outputs/final/summary.json after Hadoop Streaming validation.</footer>
</main></body></html>
""".format(
        total=int(summary["total_requests"]),
        service=esc(summary["most_requested_service"]),
        endpoint=esc(summary["slowest_endpoint"]),
        champion=esc(summary["predicted_champion"]),
        rows=service_rows(services),
        countries=country_cards(summary["popular_team_by_country"]),
    )


def main():
    args = parse_args()
    summary = read_json(args.summary)
    services = read_csv(args.service_stats)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_page(summary, services), encoding="utf-8")
    print("Dashboard written to {}".format(output))


if __name__ == "__main__":
    main()
