ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY generate.py /app/generate.py

RUN useradd --create-home --uid 10001 generator
USER 10001

ENTRYPOINT ["python", "/app/generate.py"]
