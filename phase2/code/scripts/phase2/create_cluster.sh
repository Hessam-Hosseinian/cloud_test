#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

CLUSTER_NAME="${CLUSTER_NAME:-cc-project}"

if kind get clusters 2>/dev/null | grep -Fxq "$CLUSTER_NAME"; then
  echo "kind cluster '$CLUSTER_NAME' already exists."
else
  kind create cluster \
    --name "$CLUSTER_NAME" \
    --config k8s/kind-config.yaml
fi

kubectl config use-context "kind-$CLUSTER_NAME" >/dev/null
kubectl wait --for=condition=Ready node --all --timeout=3m

# containerd runs in the kind node's host namespace, outside cluster DNS. Keep
# the stable Registry Service name resolvable there as well as inside pods.
NODE_CONTAINER="${CLUSTER_NAME}-control-plane"
if ! docker exec "$NODE_CONTAINER" getent hosts registry.cc-project.svc >/dev/null 2>&1; then
  docker exec "$NODE_CONTAINER" sh -c \
    "printf '%s\\n' '10.96.0.50 registry.cc-project.svc' >> /etc/hosts"
fi

kubectl apply -f k8s/base/00-namespace-storage.yaml

echo "Cluster context: $(kubectl config current-context)"
docker exec "$NODE_CONTAINER" getent hosts registry.cc-project.svc
kubectl get nodes -o wide
