# World Cup Log Analytics — Phase 2

Phase 2 moves the complete Phase 1 workflow to a single-node Kubernetes
cluster and automates it with a self-hosted GitLab and a Kubernetes executor
Runner. The API, traffic generator, five Hadoop Streaming jobs, validation,
dashboard generation, and publication are all managed by Kubernetes objects.

## Architecture

The `cc-project` namespace contains:

- three FastAPI Deployments and matching ClusterIP Services;
- one Nginx API gateway exposed on `http://localhost:8080`;
- a shared `project-data` PVC for gateway logs, service logs, and outputs;
- traffic, Hadoop, validation, and report Kubernetes Jobs;
- a private in-cluster registry used by Kaniko;
- a low-memory GitLab CE Deployment at `http://localhost:8929`;
- a GitLab Runner using the Kubernetes executor;
- a published dashboard at `http://localhost:9000/index.html`.

All API requests still pass through Nginx. The Hadoop StatefulSets start only
during the `mapreduce` stage and return to zero replicas afterward.

## 1. Create the kind cluster

The cluster maps the three required NodePorts to stable host ports and teaches
containerd how to pull HTTP images from the private registry Service.

```bash
chmod +x tests/*.sh hadoop-k8s/*.sh scripts/phase2/*.sh
./scripts/phase2/create_cluster.sh
./scripts/phase2/load_core_images.sh
```

## 2. Start the in-cluster GitLab

The bootstrap password and API/Runner tokens are generated locally under
`.phase2-secrets/`, which is excluded from Git. Tokens are stored in
Kubernetes Secrets, not ConfigMaps.

```bash
./scripts/phase2/deploy_gitlab.sh
./scripts/phase2/configure_gitlab.sh
```

The second command creates the real GitLab project, creates a project Runner,
deploys that Runner, initializes the local repository, and pushes `main`.
That push triggers the pipeline.

## 3. Watch the pipeline

```bash
TIMEOUT_SECONDS=5400 ./scripts/phase2/wait_for_pipeline.sh
./scripts/phase2/collect_status.sh
```

The pipeline stages are:

1. `test` — Python syntax, mapper/reducer regression, and output schema tests;
2. `build` — daemonless Kaniko builds and pushes six images;
3. `deploy` — applies Deployments, Services, ConfigMaps, PVCs, and StatefulSets;
4. `traffic` — resets the shared volume and sends requests only to Nginx;
5. `mapreduce` — starts HDFS and executes the five Hadoop Streaming jobs;
6. `validate` — validates all thirteen required Phase 1 output files;
7. `report` — generates HTML and stores the key files as GitLab artifacts;
8. `publish` — deploys and checks the report-web Service.

The default pipeline creates 100,000 requests. A shorter diagnostic run can
set the GitLab CI variable `TRAFFIC_REQUESTS` to a smaller positive value.

## 4. Verify the deployed output

```bash
curl http://localhost:8080/health
curl http://localhost:9000/summary.json
xdg-open http://localhost:9000/index.html
```

Useful live-demo commands:

```bash
kubectl get pods,svc,jobs,pvc -n cc-project
kubectl logs -n cc-project job/traffic-generator
kubectl logs -n cc-project job/mapreduce-pipeline
kubectl logs -n cc-project job/validate-output
```

## 5. Optional Spark on Kubernetes

After a successful pipeline, set `IMAGE_TAG` to its short commit SHA. The
script scales down GitLab and the API first so Spark does not compete with
them for RAM.

```bash
IMAGE_TAG=<successful-short-sha> ./scripts/phase2/run_spark_kubernetes.sh
```

Spark reads newly created JSON Lines batches from the shared PVC, computes
ten-second gateway windows and popular teams by country, and prints live
results from a Kubernetes Job.

## Resource controls

- GitLab: 1500 MiB request, 3200 MiB limit, one Puma process and two Sidekiq
  workers;
- Runner: one concurrent pipeline job;
- API services: 160 MiB limit each;
- Nginx: 80 MiB limit;
- Hadoop: scaled to zero outside its stage;
- Spark: 1600 MiB limit and `local[2]`;
- traffic generator: fixed pool of 32 workers without one Future per request.

No secret values are committed. Do not add `.phase2-secrets/` to the final
repository or submission archive.
