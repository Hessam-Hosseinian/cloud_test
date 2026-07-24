#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

NS="${NS:-cc-project}"
SECRET_DIR=".phase2-secrets"
PASSWORD_FILE="$SECRET_DIR/gitlab-root-password"

mkdir -p "$SECRET_DIR"
chmod 0700 "$SECRET_DIR"

if [[ ! -s "$PASSWORD_FILE" ]]; then
  umask 077
  openssl rand -hex 16 > "$PASSWORD_FILE"
fi

ROOT_PASSWORD="$(tr -d '\r\n' < "$PASSWORD_FILE")"

kubectl apply -f k8s/base/00-namespace-storage.yaml
kubectl apply -f k8s/base/01-registry.yaml
kubectl -n "$NS" rollout status deployment/registry --timeout=5m

kubectl -n "$NS" create secret generic gitlab-bootstrap \
  --from-literal="initial-root-password=$ROOT_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f k8s/gitlab/gitlab.yaml
kubectl apply -f k8s/runner/rbac.yaml

echo "Waiting for the low-memory GitLab deployment; first startup can take several minutes."
kubectl -n "$NS" rollout status deployment/gitlab --timeout=25m
kubectl -n "$NS" get pods,svc,pvc
curl --fail --silent --show-error --output /dev/null \
  http://localhost:8929/users/sign_in
echo
