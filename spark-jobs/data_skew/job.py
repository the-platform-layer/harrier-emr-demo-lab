#!/usr/bin/env python3
"""Data skew scenario with one intentionally dominant key."""

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
    parser.add_argument("--hot-rows", type=int, default=100000)
    parser.add_argument("--cold-rows", type=int, default=1000)
    parser.add_argument("--hot-partition-sleep-seconds", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import count, lit
    from pyspark.sql.types import IntegerType, StringType, StructField, StructType

    args = parse_args()
    spark = SparkSession.builder.appName(f"harrier-demo-data-skew-{args.run_id}").getOrCreate()

    skew_ratio = max(1, args.hot_rows // max(args.cold_rows, 1))
    signal = f"data skew detected; skew ratio {skew_ratio}; hot partition; long-tail task"
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_data_skew_started",
                "run_id": args.run_id,
                "partitions": args.partitions,
                "hot_rows": args.hot_rows,
                "cold_rows": args.cold_rows,
                "skew_ratio": skew_ratio,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )

    def build_partition(partition_index: int, _rows):
        if partition_index == 0:
            time.sleep(args.hot_partition_sleep_seconds)
            for row_id in range(args.hot_rows):
                yield ("hot_customer", partition_index, row_id)
        else:
            for row_id in range(args.cold_rows):
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
    summary = skewed.groupBy("customer_key").agg(count("*").alias("row_count"))
    summary.withColumn("run_id", lit(args.run_id)).write.mode("overwrite").json(args.output.rstrip("/"))

    print(signal)
    raise RuntimeError(signal)


if __name__ == "__main__":
    main()
