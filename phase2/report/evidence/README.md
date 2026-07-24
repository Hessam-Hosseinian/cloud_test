# Phase 2 execution evidence

These files were captured from the final Kubernetes and GitLab CI/CD execution,
not from the Phase 1 Docker Compose environment.

- Namespace: `cc-project`
- GitLab pipeline: `16`
- Commit: `f507f6c39b3de730fc187ab45cfdf2679e6b4d8a`
- Pipeline status: `success`
- Pipeline finish time: `2026-07-25 01:18:05 +03:30`
- Evidence capture date: `2026-07-25`

The Kubernetes timestamps in some outputs are UTC and therefore show
`2026-07-24`, while GitLab displays the same execution in Tehran time on
`2026-07-25`.

No password, API token, Runner token, Kubernetes Secret value, or private key
is included. The evidence can be reproduced with:

```bash
cd phase2/code
bash scripts/phase2/collect_status.sh
kubectl -n cc-project get deployments,statefulsets,services,jobs,pvc
kubectl -n cc-project logs job/mapreduce-pipeline
kubectl -n cc-project logs job/spark-streaming
```

The PNG files next to the text captures are the versions embedded in the
report. They use the same plain terminal style as the Phase 1 report and are
rendered directly from the matching text files with `pango-view`. For example:

```bash
pango-view --no-display --pixels \
  --font='DejaVu Sans Mono 18' \
  --foreground='#d8dee9' --background='#0d1117' \
  --margin=28 --spacing=2 \
  --output=04_mapreduce_and_validation.png \
  04_mapreduce_and_validation.txt
```
