#!/usr/bin/env python3
"""Low-resource Spark Structured Streaming analytics for Phase 1 logs."""

import argparse
import time
from pathlib import Path

from pyspark.sql import SparkSession, functions as F, types as T
from pyspark.sql.window import Window


NGINX_SCHEMA = T.StructType([
    T.StructField("timestamp", T.StringType()),
    T.StructField("request_id", T.StringType()),
    T.StructField("client_ip", T.StringType()),
    T.StructField("client_country", T.StringType()),
    T.StructField("scenario", T.StringType()),
    T.StructField("method", T.StringType()),
    T.StructField("path", T.StringType()),
    T.StructField("service", T.StringType()),
    T.StructField("status_code", T.IntegerType()),
    T.StructField("request_time_sec", T.StringType()),
    T.StructField("user_agent", T.StringType()),
])

SERVICE_SCHEMA = T.StructType([
    T.StructField("timestamp", T.StringType()),
    T.StructField("request_id", T.StringType()),
    T.StructField("client_country", T.StringType()),
    T.StructField("scenario", T.StringType()),
    T.StructField("service", T.StringType()),
    T.StructField("endpoint", T.StringType()),
    T.StructField("entity_type", T.StringType()),
    T.StructField("entity_value", T.StringType()),
    T.StructField("status_code", T.IntegerType()),
    T.StructField("processing_time_ms", T.DoubleType()),
    T.StructField("event_type", T.StringType()),
])


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nginx-input", required=True)
    parser.add_argument("--service-input", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--trigger-seconds", type=int, default=5)
    parser.add_argument("--run-seconds", type=int, default=0,
                        help="stop automatically after N seconds; 0 means run forever")
    return parser.parse_args()


def main():
    args = parse_args()
    Path(args.checkpoint).mkdir(parents=True, exist_ok=True)

    spark = (
        SparkSession.builder
        .appName("world-cup-live-log-analysis")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.default.parallelism", "2")
        .config("spark.driver.memory", "768m")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    nginx = (
        spark.readStream.schema(NGINX_SCHEMA).json(args.nginx_input)
        .withColumn("event_time", F.to_timestamp("timestamp"))
        .withColumn("response_time_ms", F.col("request_time_sec").cast("double") * 1000.0)
        .withColumn("endpoint", F.regexp_extract("path", r"^[^?]+", 0))
        .filter(F.col("event_time").isNotNull())
        .withWatermark("event_time", "30 seconds")
    )
    gateway_stats = (
        nginx.groupBy(F.window("event_time", "10 seconds"), "service", "endpoint")
        .agg(
            F.count("*").alias("total_requests"),
            F.sum(F.when(F.col("status_code") >= 400, 1).otherwise(0)).alias("errors"),
            F.avg("response_time_ms").alias("avg_response_time_ms"),
        )
        .withColumn("error_rate_percent", F.round(F.col("errors") * 100.0 / F.col("total_requests"), 3))
    )

    service_logs = (
        spark.readStream.schema(SERVICE_SCHEMA).json(args.service_input)
        .withColumn("event_time", F.to_timestamp("timestamp"))
        .filter((F.col("event_time").isNotNull()) &
                (F.col("entity_type") == "team") &
                (F.col("entity_value") != ""))
        .withWatermark("event_time", "30 seconds")
    )
    team_counts = (
        service_logs.groupBy(F.window("event_time", "10 seconds"), "client_country", "entity_value")
        .count()
    )

    def write_gateway(batch, epoch_id):
        ordered = batch.orderBy(F.desc("total_requests"), "service", "endpoint")
        print("\n=== LIVE GATEWAY WINDOW | epoch {} ===".format(epoch_id))
        ordered.show(20, truncate=False)

    def write_popular_teams(batch, epoch_id):
        rank_window = Window.partitionBy("window", "client_country").orderBy(
            F.desc("count"), F.asc("entity_value")
        )
        popular = (batch.withColumn("rank", F.row_number().over(rank_window))
                   .filter(F.col("rank") == 1)
                   .drop("rank")
                   .orderBy("window", "client_country"))
        print("\n=== LIVE POPULAR TEAM BY COUNTRY | epoch {} ===".format(epoch_id))
        popular.show(50, truncate=False)

    trigger = "{} seconds".format(args.trigger_seconds)
    gateway_query = (
        gateway_stats.writeStream.outputMode("update")
        .option("checkpointLocation", str(Path(args.checkpoint) / "gateway"))
        .trigger(processingTime=trigger)
        .foreachBatch(write_gateway)
        .start()
    )
    team_query = (
        team_counts.writeStream.outputMode("update")
        .option("checkpointLocation", str(Path(args.checkpoint) / "teams"))
        .trigger(processingTime=trigger)
        .foreachBatch(write_popular_teams)
        .start()
    )

    print("Structured Streaming started. Waiting for new JSONL batch files...")
    if args.run_seconds > 0:
        deadline = time.monotonic() + args.run_seconds
        try:
            while time.monotonic() < deadline:
                for query in (gateway_query, team_query):
                    if not query.isActive:
                        error = query.exception()
                        if error is not None:
                            raise RuntimeError(str(error))
                time.sleep(1)
        finally:
            for query in (gateway_query, team_query):
                if query.isActive:
                    query.stop()
    else:
        spark.streams.awaitAnyTermination()
    spark.stop()


if __name__ == "__main__":
    main()
