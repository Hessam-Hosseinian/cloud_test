#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

NS="${NS:-cc-project}"

echo "=== Kubernetes nodes ==="
kubectl get nodes -o wide
echo
echo "=== Workloads and services ==="
kubectl -n "$NS" get deployments,statefulsets,pods,services,jobs,pvc -o wide
echo
echo "=== Resource requests and limits ==="
kubectl -n "$NS" get pods -o custom-columns=\
'POD:.metadata.name,CPU_REQ:.spec.containers[*].resources.requests.cpu,MEM_REQ:.spec.containers[*].resources.requests.memory,CPU_LIM:.spec.containers[*].resources.limits.cpu,MEM_LIM:.spec.containers[*].resources.limits.memory'
echo
echo "=== Docker-level kind resource use ==="
docker stats --no-stream --format \
  'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.PIDs}}' cc-project-control-plane
