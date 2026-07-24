#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/project}"
cd "$PROJECT_ROOT"
export HADOOP_CLIENT_OPTS="${HADOOP_CLIENT_OPTS:--Xmx384m}"
STREAMING_JAR="${STREAMING_JAR:-/opt/hadoop-3.2.1/share/hadoop/tools/lib/hadoop-streaming-3.2.1.jar}"

if [[ ! -f "$STREAMING_JAR" ]]; then
  echo "Hadoop Streaming jar not found: $STREAMING_JAR" >&2
  exit 1
fi
for input_file in data/nginx/nginx_access.log data/service_logs/match_service.log data/service_logs/team_service.log data/service_logs/stadium_service.log; do
  if [[ ! -s "$input_file" ]]; then
    echo "Required input is missing or empty: $input_file" >&2
    exit 1
  fi
done

mkdir -p outputs/_raw outputs/job1 outputs/job2 outputs/job3 outputs/job4 outputs/final

run_streaming() {
  local output_path="$1"
  local mapper="$2"
  local reducer="$3"
  shift 3
  hdfs dfs -rm -r -f "$output_path" >/dev/null 2>&1 || true
  hadoop jar "$STREAMING_JAR" \
    -D mapreduce.job.reduces=1 \
    -D mapreduce.map.memory.mb=256 \
    -D mapreduce.reduce.memory.mb=256 \
    -D mapreduce.map.java.opts=-Xmx192m \
    -D mapreduce.reduce.java.opts=-Xmx192m \
    -files "$mapper,$reducer" \
    -mapper "python3 $(basename "$mapper")" \
    -reducer "python3 $(basename "$reducer")" \
    "$@" \
    -output "$output_path"
}

extract_tag() {
  python3 scripts/extract_tagged_output.py \
    --input "$1" --tag "$2" --header "$3" --output "$4"
}

echo "[1/7] Uploading immutable input snapshots to HDFS"
hdfs dfs -rm -r -f /input >/dev/null 2>&1 || true
hdfs dfs -mkdir -p /input/service_logs /input/metadata /input/cleaned
hdfs dfs -put -f data/nginx/nginx_access.log /input/nginx_access.log
hdfs dfs -put -f data/service_logs/match_service.log /input/service_logs/match_service.log
hdfs dfs -put -f data/service_logs/team_service.log /input/service_logs/team_service.log
hdfs dfs -put -f data/service_logs/stadium_service.log /input/service_logs/stadium_service.log
hdfs dfs -put -f data/predictions.json /input/metadata/predictions.json

echo "[2/7] Job 1 - parsing and cleaning"
run_streaming /output/job1 mapreduce/job1_parse_clean/mapper.py mapreduce/job1_parse_clean/reducer.py \
  -input /input/nginx_access.log -input /input/service_logs
rm -f outputs/_raw/job1.tsv
hdfs dfs -getmerge /output/job1 outputs/_raw/job1.tsv
extract_tag outputs/_raw/job1.tsv nginx \
  'timestamp,request_id,client_country,scenario,service,method,path,status_code,request_time_ms,user_agent' \
  outputs/job1/cleaned_nginx_logs.csv
extract_tag outputs/_raw/job1.tsv service \
  'timestamp,request_id,client_country,service,endpoint,entity_type,entity_value,status_code,processing_time_ms,event_type' \
  outputs/job1/cleaned_service_logs.csv
extract_tag outputs/_raw/job1.tsv invalid 'source,error,raw_line' outputs/job1/invalid_logs.csv
hdfs dfs -put -f outputs/job1/cleaned_nginx_logs.csv /input/cleaned/cleaned_nginx_logs.csv
hdfs dfs -put -f outputs/job1/cleaned_service_logs.csv /input/cleaned/cleaned_service_logs.csv

echo "[3/7] Job 2 - general Nginx aggregation"
run_streaming /output/job2 mapreduce/job2_nginx_aggregation/mapper.py mapreduce/job2_nginx_aggregation/reducer.py \
  -input /input/cleaned/cleaned_nginx_logs.csv
rm -f outputs/_raw/job2.tsv
hdfs dfs -getmerge /output/job2 outputs/_raw/job2.tsv
STATS_HEADER='name,total_requests,successful_requests,client_errors,server_errors,error_rate_percent,avg_response_time_ms'
extract_tag outputs/_raw/job2.tsv service "$STATS_HEADER" outputs/job2/service_stats.csv
extract_tag outputs/_raw/job2.tsv endpoint "$STATS_HEADER" outputs/job2/endpoint_stats.csv
extract_tag outputs/_raw/job2.tsv scenario "$STATS_HEADER" outputs/job2/scenario_stats.csv

echo "[4/7] Job 3 - country/entity request counts"
run_streaming /output/job3 mapreduce/job3_country_entity/mapper.py mapreduce/job3_country_entity/reducer.py \
  -input /input/cleaned/cleaned_service_logs.csv
rm -f outputs/_raw/job3.tsv
hdfs dfs -getmerge /output/job3 outputs/_raw/job3.tsv
extract_tag outputs/_raw/job3.tsv team 'country,team,total_requests' outputs/job3/country_team_requests.csv
extract_tag outputs/_raw/job3.tsv matchday 'country,match_day,total_requests' outputs/job3/country_matchday_requests.csv
extract_tag outputs/_raw/job3.tsv stadium 'country,entity_type,stadium_or_city,total_requests' outputs/job3/country_stadium_requests.csv

echo "[5/7] Job 4 - most popular entity by country"
run_streaming /output/job4 mapreduce/job4_popular_entity/mapper.py mapreduce/job4_popular_entity/reducer.py \
  -input /output/job3
rm -f outputs/_raw/job4.tsv
hdfs dfs -getmerge /output/job4 outputs/_raw/job4.tsv
extract_tag outputs/_raw/job4.tsv popular_team 'country,popular_team,total_requests' outputs/job4/popular_team_by_country.csv
extract_tag outputs/_raw/job4.tsv popular_matchday 'country,popular_match_day,total_requests' outputs/job4/popular_matchday_by_country.csv
extract_tag outputs/_raw/job4.tsv popular_stadium 'country,entity_type,popular_stadium_or_city,total_requests' outputs/job4/popular_stadium_by_country.csv

echo "[6/7] Job 5 - final summary"
run_streaming /output/job5 mapreduce/job5_final_report/mapper.py mapreduce/job5_final_report/reducer.py \
  -input /output/job2 -input /output/job3 -input /output/job4 -input /input/metadata
rm -f outputs/final/summary.json
hdfs dfs -getmerge /output/job5 outputs/final/summary.json

echo "[7/7] Validating required outputs"
python3 scripts/validate_outputs.py
echo "MapReduce pipeline completed successfully."
