#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p data/stream/nginx data/stream/services checkpoints/spark

docker compose -f spark/docker-compose.yml run --rm spark \
  --master 'local[2]' \
  --driver-memory 768m \
  --conf spark.sql.shuffle.partitions=2 \
  spark/streaming_app.py \
  --nginx-input data/stream/nginx \
  --service-input data/stream/services \
  --checkpoint checkpoints/spark \
  --trigger-seconds 5
