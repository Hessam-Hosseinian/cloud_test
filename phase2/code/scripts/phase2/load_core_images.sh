#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

CLUSTER_NAME="${CLUSTER_NAME:-cc-project}"
IMAGES=(
  "registry:2.8.3"
  "busybox:1.36"
  "nginx:alpine"
  "python:3.12-slim"
  "chinayin/kaniko-project:v1.23.2-debug"
  "alpine/k8s:1.32.3"
  "gitlab/gitlab-runner-helper:x86_64-v17.11.1"
  "gitlab/gitlab-ce:17.11.7-ce.0"
  "gitlab/gitlab-runner:alpine-v17.11.1"
  "registry.docker.ir/bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8"
  "registry.docker.ir/bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8"
)

for image in "${IMAGES[@]}"; do
  echo "Checking registry access for $image..."
  docker manifest inspect "$image" >/dev/null
done

echo "All image references are available."
echo "The kind node will pull them directly when each workload starts."
