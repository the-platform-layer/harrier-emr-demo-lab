#!/usr/bin/env python3
"""DB partition hotspot scenario with intentionally poor JDBC bounds."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--partition-column", default="customer_id")
    parser.add_argument("--lower-bound", type=int, default=1)
    parser.add_argument("--upper-bound", type=int, default=1000000)
    parser.add_argument("--num-partitions", type=int, default=1)
    parser.add_argument("--dominant-range-rows", type=int, default=250000)
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import count, lit

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-db-partition-hotspot-{args.run_id}"
    ).getOrCreate()

    signal = (
        f"JDBC partitionColumn {args.partition_column} has numPartitions={args.num_partitions} "
        f"lowerBound={args.lower_bound} upperBound={args.upper_bound}; partition hotspot"
    )
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_db_partition_hotspot_started",
                "run_id": args.run_id,
                "partition_column": args.partition_column,
                "lower_bound": args.lower_bound,
                "upper_bound": args.upper_bound,
                "num_partitions": args.num_partitions,
                "dominant_range_rows": args.dominant_range_rows,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )

    rows = spark.range(args.dominant_range_rows).selectExpr(
        "CASE WHEN id < 240000 THEN 1 ELSE CAST(id AS INT) END AS jdbc_partition",
        "id AS row_id",
    )
    summary = rows.groupBy("jdbc_partition").agg(count("*").alias("row_count"))
    summary.withColumn("run_id", lit(args.run_id)).write.mode("overwrite").json(args.output.rstrip("/"))

    print(signal)
    raise RuntimeError(signal)


if __name__ == "__main__":
    main()
