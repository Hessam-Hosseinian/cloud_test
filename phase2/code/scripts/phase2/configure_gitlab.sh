#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

NS="${NS:-cc-project}"
GITLAB_URL="${GITLAB_URL:-http://localhost:8929}"
PROJECT_PATH="${PROJECT_PATH:-cloud-phase2}"
SECRET_DIR=".phase2-secrets"
PAT_FILE="$SECRET_DIR/gitlab-api-token"
RUNNER_FILE="$SECRET_DIR/gitlab-runner-token"

mkdir -p "$SECRET_DIR"
chmod 0700 "$SECRET_DIR"

echo "Creating a short-lived local API token inside GitLab..."
PAT="$(
  kubectl -n "$NS" exec deploy/gitlab -- gitlab-rails runner "
    require 'securerandom'
    user = User.find_by_username('root')
    raw = 'glpat-' + SecureRandom.hex(16)
    old = user.personal_access_tokens.find_by(name: 'phase2-bootstrap')
    old.revoke! if old && !old.revoked?
    token = user.personal_access_tokens.create!(
      name: 'phase2-bootstrap',
      scopes: ['api'],
      expires_at: 7.days.from_now
    )
    token.set_token(raw)
    token.save!
    puts raw
  " | tail -n 1
)"
umask 077
printf '%s\n' "$PAT" > "$PAT_FILE"

PROJECT_JSON="$(
  curl --fail --silent --show-error \
    --header "PRIVATE-TOKEN: $PAT" \
    "$GITLAB_URL/api/v4/projects/root%2F$PROJECT_PATH" 2>/dev/null || true
)"

if [[ -z "$PROJECT_JSON" ]]; then
  PROJECT_JSON="$(
    curl --fail --silent --show-error \
      --request POST \
      --header "PRIVATE-TOKEN: $PAT" \
      --data-urlencode "name=$PROJECT_PATH" \
      --data-urlencode "path=$PROJECT_PATH" \
      --data "visibility=private" \
      "$GITLAB_URL/api/v4/projects"
  )"
fi

PROJECT_ID="$(
  PROJECT_JSON="$PROJECT_JSON" python3 -c \
    'import json, os; print(json.loads(os.environ["PROJECT_JSON"])["id"])'
)"
echo "GitLab project id: $PROJECT_ID"

RUNNER_JSON="$(
  curl --fail --silent --show-error \
    --request POST \
    --header "PRIVATE-TOKEN: $PAT" \
    --data "runner_type=project_type" \
    --data "project_id=$PROJECT_ID" \
    --data-urlencode "description=cc-project-kubernetes-runner" \
    --data "run_untagged=true" \
    "$GITLAB_URL/api/v4/user/runners"
)"
RUNNER_TOKEN="$(
  RUNNER_JSON="$RUNNER_JSON" python3 -c \
    'import json, os; print(json.loads(os.environ["RUNNER_JSON"])["token"])'
)"
printf '%s\n' "$RUNNER_TOKEN" > "$RUNNER_FILE"

kubectl -n "$NS" create secret generic gitlab-runner-auth \
  --from-literal="runner-token=$RUNNER_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/runner/runner.yaml
kubectl -n "$NS" rollout status deployment/gitlab-runner --timeout=5m

if [[ ! -d .git ]]; then
  git init -b main
  git config user.name "Cloud Project Group"
  git config user.email "cloud-project@local.invalid"
fi

git add .
if ! git diff --cached --quiet; then
  git commit -m "Implement Kubernetes and GitLab CI/CD for phase 2"
fi

git remote remove gitlab-local >/dev/null 2>&1 || true
git remote add gitlab-local "$GITLAB_URL/root/$PROJECT_PATH.git"
AUTH_HEADER="$(
  printf 'oauth2:%s' "$PAT" | base64 | tr -d '\r\n'
)"
git -c credential.helper= \
  -c "http.extraHeader=Authorization: Basic $AUTH_HEADER" \
  push --set-upstream gitlab-local main

echo "Repository pushed. The GitLab pipeline should now be queued."
kubectl -n "$NS" get pods
