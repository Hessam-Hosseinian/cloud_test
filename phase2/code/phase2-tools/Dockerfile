ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /project
COPY scripts/validate_outputs.py /project/scripts/validate_outputs.py
COPY scripts/export_log_batches.py /project/scripts/export_log_batches.py
COPY report-web/generate_dashboard.py /project/report-web/generate_dashboard.py

RUN useradd --create-home --uid 10001 phase2 \
    && chown -R phase2:phase2 /project

USER 10001
ENTRYPOINT ["python"]
