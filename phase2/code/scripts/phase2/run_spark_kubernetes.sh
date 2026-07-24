#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

NS="${NS:-cc-project}"
IMAGE_TAG="${IMAGE_TAG:?set IMAGE_TAG to the successful pipeline image tag}"

restore_services() {
  local exit_code=$?
  trap - EXIT
  set +e
  echo "Restoring the services paused for the Spark resource window..."
  kubectl -n "$NS" scale deployment \
    gitlab gitlab-runner nginx-gateway match-service team-service stadium-service \
    --replicas=1
  kubectl -n "$NS" rollout status deployment/gitlab --timeout=25m
  kubectl -n "$NS" rollout status deployment/gitlab-runner --timeout=5m
  kubectl -n "$NS" rollout status deployment/nginx-gateway --timeout=5m
  kubectl -n "$NS" rollout status deployment/match-service --timeout=5m
  kubectl -n "$NS" rollout status deployment/team-service --timeout=5m
  kubectl -n "$NS" rollout status deployment/stadium-service --timeout=5m
  return "$exit_code"
}
trap restore_services EXIT

kubectl -n "$NS" create configmap spark-streaming-app \
  --from-file=streaming_app.py=spark/streaming_app.py \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "$NS" scale deployment gitlab gitlab-runner --replicas=0
kubectl -n "$NS" scale deployment nginx-gateway match-service team-service stadium-service --replicas=0
kubectl -n "$NS" delete job spark-streaming spark-export-batches --ignore-not-found

kubectl apply -f k8s/spark/spark-job.yaml
kubectl -n "$NS" wait --for=condition=Ready pod -l app=spark-streaming --timeout=5m

sed "s|__IMAGE_TAG__|$IMAGE_TAG|g" \
  k8s/spark/export-batches-job.yaml | kubectl apply -f -
kubectl -n "$NS" wait --for=condition=complete job/spark-export-batches --timeout=5m
kubectl -n "$NS" wait --for=condition=complete job/spark-streaming --timeout=5m

kubectl -n "$NS" logs job/spark-export-batches
kubectl -n "$NS" logs job/spark-streaming
