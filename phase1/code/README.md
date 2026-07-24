# World Cup Log Analytics — Phase 1

## 1. Backend services and Nginx

```bash
docker compose up --build -d
docker compose ps
docker compose exec nginx nginx -t
```

All public requests must go through `http://localhost:8080`. The backend
containers intentionally publish no host ports.

## 2. Debug and final traffic

```bash
python3 traffic-generator/generate.py --requests 1000 --workers 8 --nginx-url http://localhost:8080
python3 traffic-generator/generate.py --requests 100000 --workers 32 --nginx-url http://localhost:8080
```

The worker count is bounded to keep memory and CPU usage predictable. Nginx
writes `data/nginx/nginx_access.log`; services write JSON Lines files under
`data/service_logs/`.

For a clean run, truncate live logs without deleting their inodes:

```bash
: > data/nginx/nginx_access.log
: > data/service_logs/match_service.log
: > data/service_logs/team_service.log
: > data/service_logs/stadium_service.log
```

## 3. Hadoop Streaming pipeline

Stop the API stack before Hadoop to keep peak memory low. The generated log
files remain on the host.

```bash
docker compose down
docker compose -f hadoop/docker-compose.yml up -d
docker compose -f hadoop/docker-compose.yml ps
docker compose -f hadoop/docker-compose.yml exec namenode bash /project/scripts/run_mapreduce.sh
docker compose -f hadoop/docker-compose.yml down
```

The script executes Jobs 1 through 5, copies intermediate results to
`outputs/job*/`, creates `outputs/final/summary.json`, and validates all output
schemas. Hadoop tasks are configured for 256 MB and a single reducer; the
NameNode and DataNode containers also have explicit resource limits.

## 4. Optional Spark Structured Streaming

Keep Hadoop and the API stack stopped while running this low-resource demo.
The Spark container is limited to two CPUs and 1600 MB, while the driver uses
768 MB. Start the two streaming queries in the first terminal:

```bash
./scripts/run_spark_demo.sh
```

While Spark is waiting, create new atomic JSON Lines batch files from the final
logs in another terminal:

```bash
python3 scripts/export_log_batches.py \
  --source data/nginx/nginx_access.log \
  --output data/stream/nginx --prefix nginx \
  --batch-size 200 --max-lines 1000 --delay 0.4

python3 scripts/export_log_batches.py \
  --source data/service_logs/team_service.log \
  --output data/stream/services --prefix team \
  --batch-size 200 --max-lines 1000 --delay 0.4
```

The terminal updates ten-second gateway windows and the most popular team for
each country. Checkpoints are kept under `checkpoints/spark/`. Stop the demo
with `Ctrl+C` after the live output appears.

## 5. Required output

The final result is available at `outputs/final/summary.json`. To inspect files
in a browser:

```bash
python3 -m http.server 9000
```
