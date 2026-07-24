# Cloud Computing Final Project

Implementation of the Cloud Computing final project at Amirkabir University
of Technology. The repository contains both project phases, the generated
datasets and analysis outputs, the final reports, and the assignment PDFs.

## Team

| Student | Student ID |
|---|---:|
| سید حسام‌الدین حسینیان | 40231901 |
| فروزان قویدل | 40231064 |

## Project overview

The project implements a World Cup log-processing platform in two steps:

- **Phase 1:** three FastAPI services, an Nginx gateway, a controlled
  100,000-request traffic generator, Hadoop Streaming analytics, final CSV/JSON
  outputs, and an optional Spark Structured Streaming workload.
- **Phase 2:** migration of the complete system to Kubernetes, a self-hosted
  GitLab CE and Kubernetes-executor Runner, a private Registry, daemonless
  Kaniko builds, an eight-stage CI/CD pipeline, HDFS workloads, output
  validation, dashboard generation, publication, and an optional low-resource
  Spark Job.

The final Phase 2 CI execution was pipeline **#16** for commit `f507f6c3`.
All stages from test through publish completed successfully in 372 seconds.
The verified result contains:

- 100,000 unique Nginx requests;
- 100,000 matching backend log records;
- five completed Hadoop Streaming analysis jobs;
- thirteen validated required output files;
- a generated HTML dashboard and final JSON summary;
- a successful Spark Structured Streaming Job with no container restart.

## Repository layout

```text
.
├── phase1/
│   ├── assignment.pdf
│   ├── code/
│   │   ├── data/
│   │   ├── outputs/
│   │   ├── match-service/
│   │   ├── team-service/
│   │   ├── stadium-service/
│   │   ├── traffic-generator/
│   │   ├── mapreduce/
│   │   └── spark/
│   └── report/
│       ├── report.pdf
│       ├── report.tex
│       └── evidence/
└── phase2/
    ├── assignment.pdf
    ├── code/
    │   ├── .gitlab-ci.yml
    │   ├── data/
    │   ├── outputs/
    │   ├── k8s/
    │   ├── scripts/phase2/
    │   ├── hadoop-k8s/
    │   ├── phase2-tools/
    │   ├── report-web/
    │   └── docs/
    └── report/
        ├── report.pdf
        ├── report.tex
        ├── architecture.png
        └── evidence/
```

## Reports

- [Phase 1 report](phase1/report/report.pdf)
- [Phase 2 report](phase2/report/report.pdf)
- [Final Phase 2 architecture](phase2/report/architecture.png)
- [Sanitized Phase 2 execution evidence](phase2/report/evidence/README.md)
- [Published dashboard snapshot](phase2/code/outputs/final/index.html)

Both reports include the implementation procedure, commands, test results,
resource controls, encountered errors, and their fixes.

The Phase 2 evidence directory contains the final Kubernetes workload state,
all thirteen GitLab Pipeline 16 jobs, exact traffic and output counts,
MapReduce validation, HTTP publication checks, and the successful Kubernetes
Spark execution. These files are plain text so they can be reviewed directly
on GitHub without access to the original local GitLab instance.

## Running Phase 1

```bash
cd phase1/code
docker compose up -d --build
```

The Phase 1 README contains the complete traffic, Hadoop, validation, and Spark
commands:

- [Phase 1 instructions](phase1/code/README.md)

## Running Phase 2

Prerequisites are Docker, kind, kubectl, Git, curl, and OpenSSL.

```bash
cd phase2/code
bash scripts/phase2/create_cluster.sh
bash scripts/phase2/load_core_images.sh
bash scripts/phase2/deploy_gitlab.sh
bash scripts/phase2/configure_gitlab.sh
bash scripts/phase2/wait_for_pipeline.sh
```

After a successful deployment:

- GitLab: `http://localhost:8929`
- Nginx API: `http://localhost:8080`
- Dashboard: `http://localhost:9000/index.html`

Detailed installation, verification, troubleshooting, and Spark instructions
are available in the [Phase 2 README](phase2/code/README.md).

## Resource controls

The implementation was tested on a machine with 7.4 GiB of RAM. To prevent
resource exhaustion:

- the GitLab Runner executes one CI job at a time;
- HDFS is scaled to zero outside the MapReduce stage;
- Spark uses `local[2]` with a 1600 MiB container limit;
- GitLab and the API services are paused during the optional Spark run;
- the output validator processes CSV files as streams;
- the traffic generator uses a bounded worker pool.

## Repository safety

No GitLab password, API token, Runner token, private key, or local Secret file
is stored in this repository. Runtime HDFS block storage, checkpoints, caches,
Python bytecode, and LaTeX temporary files are intentionally excluded.
