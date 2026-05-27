#!/usr/bin/env python3
"""Long-running data-delay scenario with an intentionally slow skewed partition."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--partitions", type=int, default=24)
    parser.add_argument("--hot-partition-sleep-seconds", type=int, default=900)
    parser.add_argument("--hot-rows", type=int, default=200000)
    parser.add_argument("--rows-per-cold-partition", type=int, default=2000)
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import count, current_timestamp, lit
    from pyspark.sql.types import IntegerType, StringType, StructField, StructType

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-long-running-data-delay-{args.run_id}"
    ).getOrCreate()

    print(
        json.dumps(
            {
                "event": "harrier_demo_long_running_data_delay_started",
                "run_id": args.run_id,
                "partitions": args.partitions,
                "hot_partition_sleep_seconds": args.hot_partition_sleep_seconds,
                "hot_rows": args.hot_rows,
                "rows_per_cold_partition": args.rows_per_cold_partition,
            },
            sort_keys=True,
        )
    )

    def build_partition(partition_index: int, _rows):
        if partition_index == 0:
            print(
                json.dumps(
                    {
                        "event": "harrier_demo_hot_partition_sleeping",
                        "partition": partition_index,
                        "sleep_seconds": args.hot_partition_sleep_seconds,
                    },
                    sort_keys=True,
                )
            )
            time.sleep(args.hot_partition_sleep_seconds)
            for row_id in range(args.hot_rows):
                yield ("hot_customer", partition_index, row_id)
        else:
            for row_id in range(args.rows_per_cold_partition):
                yield (f"cold_customer_{partition_index:03d}", partition_index, row_id)

    schema = StructType(
        [
            StructField("customer_key", StringType(), nullable=False),
            StructField("source_partition", IntegerType(), nullable=False),
            StructField("row_id", IntegerType(), nullable=False),
        ]
    )
    base = spark.sparkContext.parallelize(range(args.partitions), args.partitions)
    skewed = spark.createDataFrame(base.mapPartitionsWithIndex(build_partition), schema=schema)
    summary = (
        skewed.groupBy("customer_key")
        .agg(count("*").alias("row_count"))
        .withColumn("run_id", lit(args.run_id))
        .withColumn("processed_at", current_timestamp())
        .cache()
    )

    summary_rows = summary.count()
    summary.write.mode("overwrite").parquet(args.output.rstrip("/"))
    print(
        json.dumps(
            {
                "event": "harrier_demo_long_running_data_delay_complete",
                "run_id": args.run_id,
                "output": args.output.rstrip("/"),
                "summary_rows": summary_rows,
            },
            sort_keys=True,
        )
    )
    spark.stop()


if __name__ == "__main__":
    main()
