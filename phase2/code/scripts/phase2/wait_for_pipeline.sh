#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

GITLAB_URL="${GITLAB_URL:-http://localhost:8929}"
PROJECT_PATH="${PROJECT_PATH:-cloud-phase2}"
PAT_FILE=".phase2-secrets/gitlab-api-token"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-5400}"

if [[ ! -s "$PAT_FILE" ]]; then
  echo "Missing API token file: $PAT_FILE" >&2
  exit 1
fi

PAT="$(tr -d '\r\n' < "$PAT_FILE")"
PROJECT_ID="$(
  curl --fail --silent --show-error \
    --header "PRIVATE-TOKEN: $PAT" \
    "$GITLAB_URL/api/v4/projects/root%2F$PROJECT_PATH" |
    python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"

started="$(date +%s)"
while :; do
  pipeline="$(
    curl --fail --silent --show-error \
      --header "PRIVATE-TOKEN: $PAT" \
      "$GITLAB_URL/api/v4/projects/$PROJECT_ID/pipelines?per_page=1"
  )"
  status="$(
    PIPELINE_JSON="$pipeline" python3 -c \
      'import json,os; rows=json.loads(os.environ["PIPELINE_JSON"]); print(rows[0]["status"] if rows else "missing")'
  )"
  pipeline_id="$(
    PIPELINE_JSON="$pipeline" python3 -c \
      'import json,os; rows=json.loads(os.environ["PIPELINE_JSON"]); print(rows[0]["id"] if rows else "")'
  )"
  printf 'pipeline=%s status=%s time=%s\n' "$pipeline_id" "$status" "$(date +%H:%M:%S)"

  case "$status" in
    success)
      exit 0
      ;;
    failed|canceled|skipped)
      echo "Pipeline finished with status: $status" >&2
      exit 1
      ;;
  esac

  if (( $(date +%s) - started > TIMEOUT_SECONDS )); then
    echo "Timed out waiting for pipeline." >&2
    exit 1
  fi
  sleep 15
done
