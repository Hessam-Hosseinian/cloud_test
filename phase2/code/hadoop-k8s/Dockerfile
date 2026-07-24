ARG BASE_IMAGE=eclipse-temurin:11-jre-jammy
FROM ${BASE_IMAGE}

ARG HADOOP_VERSION=3.4.3

RUN apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       aria2 ca-certificates python3 \
    && aria2c --continue=true --max-connection-per-server=8 \
       --split=8 --min-split-size=1M --file-allocation=none \
       --console-log-level=warn --summary-interval=30 \
       --dir=/tmp --out=hadoop.tar.gz \
       "https://dlcdn.apache.org/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz" \
    && tar -xzf /tmp/hadoop.tar.gz -C /opt \
    && rm -f /tmp/hadoop.tar.gz \
    && ln -s "/opt/hadoop-${HADOOP_VERSION}" /opt/hadoop \
    && rm -rf /opt/hadoop/share/doc /var/lib/apt/lists/*

ENV HADOOP_HOME=/opt/hadoop \
    HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop \
    PATH=/opt/hadoop/bin:/opt/hadoop/sbin:${PATH} \
    JAVA_HOME=/opt/java/openjdk

COPY hadoop-k8s/core-site.xml /opt/hadoop/etc/hadoop/core-site.xml
COPY hadoop-k8s/mapred-site.xml /opt/hadoop/etc/hadoop/mapred-site.xml

WORKDIR /project
COPY mapreduce /project/mapreduce
COPY scripts/extract_tagged_output.py /project/scripts/extract_tagged_output.py
COPY scripts/run_mapreduce.sh /project/scripts/run_mapreduce.sh
COPY scripts/validate_outputs.py /project/scripts/validate_outputs.py
COPY data/predictions.json /project/bootstrap/predictions.json
COPY hadoop-k8s/run-on-kubernetes.sh /project/scripts/run-on-kubernetes.sh

RUN chmod +x /project/scripts/*.sh /project/mapreduce/*/*.py

ENTRYPOINT ["/bin/bash", "/project/scripts/run-on-kubernetes.sh"]
