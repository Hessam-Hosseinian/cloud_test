#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
TEST_DIR="$(mktemp -d)"
trap 'find "$TEST_DIR" -type f -delete; rmdir "$TEST_DIR"' EXIT

for input_file in data/nginx/nginx_access.log data/service_logs/*.log; do
  python3 mapreduce/job1_parse_clean/mapper.py < "$input_file"
done | LC_ALL=C sort | python3 mapreduce/job1_parse_clean/reducer.py > "$TEST_DIR/job1.tsv"

python3 scripts/extract_tagged_output.py --input "$TEST_DIR/job1.tsv" --tag nginx \
  --header 'timestamp,request_id,client_country,scenario,service,method,path,status_code,request_time_ms,user_agent' \
  --output "$TEST_DIR/cleaned_nginx.csv"
python3 scripts/extract_tagged_output.py --input "$TEST_DIR/job1.tsv" --tag service \
  --header 'timestamp,request_id,client_country,service,endpoint,entity_type,entity_value,status_code,processing_time_ms,event_type' \
  --output "$TEST_DIR/cleaned_service.csv"

python3 mapreduce/job2_nginx_aggregation/mapper.py < "$TEST_DIR/cleaned_nginx.csv" \
  | LC_ALL=C sort | python3 mapreduce/job2_nginx_aggregation/reducer.py > "$TEST_DIR/job2.tsv"
python3 mapreduce/job3_country_entity/mapper.py < "$TEST_DIR/cleaned_service.csv" \
  | LC_ALL=C sort | python3 mapreduce/job3_country_entity/reducer.py > "$TEST_DIR/job3.tsv"
python3 mapreduce/job4_popular_entity/mapper.py < "$TEST_DIR/job3.tsv" \
  | LC_ALL=C sort | python3 mapreduce/job4_popular_entity/reducer.py > "$TEST_DIR/job4.tsv"

for input_file in "$TEST_DIR/job2.tsv" "$TEST_DIR/job3.tsv" "$TEST_DIR/job4.tsv" data/predictions.json; do
  python3 mapreduce/job5_final_report/mapper.py < "$input_file"
done | LC_ALL=C sort | python3 mapreduce/job5_final_report/reducer.py > "$TEST_DIR/summary.json"

python3 -m json.tool "$TEST_DIR/summary.json"
echo "Local pipeline test passed. Temporary files were removed."
