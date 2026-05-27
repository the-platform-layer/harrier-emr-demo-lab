#!/usr/bin/env python3
"""Long-running resource-delay scenario that holds many tasks open."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--tasks", type=int, default=96)
    parser.add_argument("--sleep-seconds", type=int, default=900)
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql.types import IntegerType, StructField, StructType

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-long-running-resource-delay-{args.run_id}"
    ).getOrCreate()

    print(
        json.dumps(
            {
                "event": "harrier_demo_long_running_resource_delay_started",
                "run_id": args.run_id,
                "tasks": args.tasks,
                "sleep_seconds": args.sleep_seconds,
            },
            sort_keys=True,
        )
    )

    def hold_partition(partition_index: int, _rows):
        print(
            json.dumps(
                {
                    "event": "harrier_demo_resource_delay_task_sleeping",
                    "partition": partition_index,
                    "sleep_seconds": args.sleep_seconds,
                },
                sort_keys=True,
            )
        )
        time.sleep(args.sleep_seconds)
        yield (partition_index, args.sleep_seconds)

    schema = StructType(
        [
            StructField("task_id", IntegerType(), nullable=False),
            StructField("sleep_seconds", IntegerType(), nullable=False),
        ]
    )
    base = spark.sparkContext.parallelize(range(args.tasks), args.tasks)
    held = spark.createDataFrame(base.mapPartitionsWithIndex(hold_partition), schema=schema).cache()
    tasks_completed = held.count()
    held.write.mode("overwrite").json(args.output.rstrip("/"))

    print(
        json.dumps(
            {
                "event": "harrier_demo_long_running_resource_delay_complete",
                "run_id": args.run_id,
                "output": args.output.rstrip("/"),
                "tasks_completed": tasks_completed,
            },
            sort_keys=True,
        )
    )
    spark.stop()


if __name__ == "__main__":
    main()
