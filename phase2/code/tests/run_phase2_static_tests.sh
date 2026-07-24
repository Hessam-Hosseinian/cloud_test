#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 -m py_compile \
  match-service/main.py \
  team-service/main.py \
  stadium-service/main.py \
  traffic-generator/generate.py \
  phase2-tools/../report-web/generate_dashboard.py \
  scripts/*.py \
  mapreduce/*/*.py

for script in scripts/*.sh scripts/phase2/*.sh hadoop-k8s/*.sh; do
  bash -n "$script"
done

[[ "$(grep -c 'name: SERVICE_LOG_PATH' k8s/base/02-backends.yaml)" -eq 3 ]]
[[ "$(grep -c '/project-data/data/service_logs/' k8s/base/02-backends.yaml)" -eq 3 ]]
[[ "$(grep -c 'mkdir -p /project-data/data/service_logs' k8s/base/02-backends.yaml)" -eq 3 ]]
if grep -q 'name: LOG_PATH' k8s/base/02-backends.yaml; then
  echo "Backend manifest uses the wrong logging environment variable." >&2
  exit 1
fi
echo "Backend PVC log-path regression check passed."

PHASE2_TEST_FIXTURES=1 bash scripts/run_local_pipeline_test.sh

dedup_output="$(
  {
    head -n 1 tests/fixtures/nginx.jsonl
    head -n 1 tests/fixtures/nginx.jsonl
    head -n 1 tests/fixtures/services.jsonl
    head -n 1 tests/fixtures/services.jsonl
  } | python3 mapreduce/job1_parse_clean/mapper.py \
    | LC_ALL=C sort \
    | python3 mapreduce/job1_parse_clean/reducer.py
)"
[[ "$(grep -c $'^nginx\t' <<< "$dedup_output")" -eq 1 ]]
[[ "$(grep -c $'^service\t' <<< "$dedup_output")" -eq 1 ]]
echo "Job 1 duplicate-request regression check passed."

if [[ -f outputs/final/summary.json ]]; then
  EXPECTED_REQUESTS=100000 python3 scripts/validate_outputs.py
  echo "Existing Phase 1 outputs also passed the regression checks."
fi

echo "Static checks and the five-stage MapReduce fixture test passed."
