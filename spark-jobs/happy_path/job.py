#!/usr/bin/env python3
"""Known-good PySpark job for proving the demo EMR environment works."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="CSV input path, usually s3://.../events.csv")
    parser.add_argument("--output", required=True, help="S3 output prefix for processed data")
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--coalesce", type=int, default=1, help="Number of output files per aggregate")
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import (
        avg,
        col,
        count,
        countDistinct,
        current_timestamp,
        lit,
        round,
        sum,
        to_date,
        to_timestamp,
    )
    from pyspark.sql.types import DoubleType, StringType, StructField, StructType

    args = parse_args()
    output_prefix = args.output.rstrip("/")

    spark = (
        SparkSession.builder.appName(f"harrier-demo-happy-path-{args.run_id}")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )

    schema = StructType(
        [
            StructField("event_id", StringType(), nullable=False),
            StructField("customer_id", StringType(), nullable=False),
            StructField("event_type", StringType(), nullable=False),
            StructField("amount", DoubleType(), nullable=False),
            StructField("event_ts", StringType(), nullable=False),
            StructField("country", StringType(), nullable=False),
        ]
    )

    raw_events = spark.read.option("header", "true").schema(schema).csv(args.input)
    events = (
        raw_events.withColumn("event_timestamp", to_timestamp(col("event_ts"), "yyyy-MM-dd'T'HH:mm:ssX"))
        .withColumn("event_date", to_date(col("event_timestamp")))
        .withColumn("run_id", lit(args.run_id))
    )

    daily_country = (
        events.groupBy("run_id", "event_date", "country")
        .agg(
            count("*").alias("event_count"),
            countDistinct("customer_id").alias("unique_customers"),
            round(sum("amount"), 2).alias("net_amount"),
            round(avg("amount"), 2).alias("average_amount"),
        )
        .withColumn("processed_at", current_timestamp())
    )

    event_type_summary = (
        events.groupBy("run_id", "event_type")
        .agg(
            count("*").alias("event_count"),
            round(sum("amount"), 2).alias("net_amount"),
        )
        .withColumn("processed_at", current_timestamp())
    )

    daily_country.coalesce(args.coalesce).write.mode("overwrite").partitionBy("event_date").parquet(
        f"{output_prefix}/daily_country"
    )
    event_type_summary.coalesce(args.coalesce).write.mode("overwrite").parquet(
        f"{output_prefix}/event_type_summary"
    )

    metrics = {
        "event": "harrier_demo_happy_path_complete",
        "run_id": args.run_id,
        "input": args.input,
        "output": output_prefix,
        "input_rows": events.count(),
        "daily_country_rows": daily_country.count(),
        "event_type_rows": event_type_summary.count(),
    }
    print(json.dumps(metrics, sort_keys=True))
    spark.stop()


if __name__ == "__main__":
    main()
