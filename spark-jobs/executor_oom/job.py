#!/usr/bin/env python3
"""Executor-side memory pressure scenario for Harrier demos."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--partitions", type=int, default=4)
    parser.add_argument("--allocation-mb", type=int, default=768)
    parser.add_argument("--chunk-mb", type=int, default=64)
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql.types import IntegerType, StructField, StructType

    args = parse_args()
    spark = SparkSession.builder.appName(f"harrier-demo-executor-oom-{args.run_id}").getOrCreate()

    print(
        json.dumps(
            {
                "event": "harrier_demo_executor_oom_started",
                "run_id": args.run_id,
                "partitions": args.partitions,
                "allocation_mb": args.allocation_mb,
            },
            sort_keys=True,
        )
    )

    def pressure_partition(partition_index: int, _rows):
        signal = (
            f"executor {partition_index} java.lang.OutOfMemoryError: Java heap space; "
            "container killed by YARN for exceeding physical memory"
        )
        print(signal)
        print(
            json.dumps(
                {
                    "event": "harrier_demo_executor_oom_allocation_started",
                    "partition": partition_index,
                    "allocation_mb": args.allocation_mb,
                    "log_signal": signal,
                },
                sort_keys=True,
            )
        )

        blocks = []
        chunk_bytes = max(1, args.chunk_mb) * 1024 * 1024
        target_bytes = max(1, args.allocation_mb) * 1024 * 1024
        allocated = 0
        try:
            while allocated < target_bytes:
                block = bytearray(chunk_bytes)
                block[0] = partition_index % 255
                block[-1] = partition_index % 255
                blocks.append(block)
                allocated += chunk_bytes
        except MemoryError:
            print(signal)
            raise

        raise RuntimeError(signal)
        yield (partition_index, allocated)  # pragma: no cover

    schema = StructType(
        [
            StructField("partition", IntegerType(), nullable=False),
            StructField("allocated_bytes", IntegerType(), nullable=False),
        ]
    )
    base = spark.sparkContext.parallelize(range(args.partitions), args.partitions)
    spark.createDataFrame(base.mapPartitionsWithIndex(pressure_partition), schema=schema).count()


if __name__ == "__main__":
    main()
