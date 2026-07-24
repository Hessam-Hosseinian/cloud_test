#!/usr/bin/env bash
set -euo pipefail

SHARED_ROOT="${SHARED_ROOT:-/project-data}"

mkdir -p \
  "$SHARED_ROOT/data/nginx" \
  "$SHARED_ROOT/data/service_logs" \
  "$SHARED_ROOT/outputs"

if [[ ! -f "$SHARED_ROOT/data/predictions.json" ]]; then
  cp /project/bootstrap/predictions.json "$SHARED_ROOT/data/predictions.json"
fi

rm -rf /project/data /project/outputs
ln -s "$SHARED_ROOT/data" /project/data
ln -s "$SHARED_ROOT/outputs" /project/outputs

echo "Using shared Kubernetes volume at $SHARED_ROOT"

safe_mode_status=""
for attempt in $(seq 1 90); do
  safe_mode_status="$(hdfs dfsadmin -safemode get 2>/dev/null || true)"
  if [[ "$safe_mode_status" == *"OFF"* ]]; then
    echo "HDFS safe mode is OFF; writes are enabled."
    break
  fi
  if (( attempt == 1 || attempt % 10 == 0 )); then
    echo "Waiting for HDFS to leave safe mode (attempt $attempt/90)..."
  fi
  sleep 2
done

if [[ "$safe_mode_status" != *"OFF"* ]]; then
  echo "HDFS did not leave safe mode within 180 seconds." >&2
  exit 1
fi

exec bash /project/scripts/run_mapreduce.sh
