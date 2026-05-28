#!/usr/bin/env python3
"""Shuffle spill scenario with a wide aggregation marker."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--rows", type=int, default=50000)
    parser.add_argument("--keys", type=int, default=64)
    parser.add_argument("--payload-bytes", type=int, default=256)
    parser.add_argument("--shuffle-partitions", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import count

    args = parse_args()
    spark = (
        SparkSession.builder.appName(f"harrier-demo-shuffle-spill-{args.run_id}")
        .config("spark.sql.shuffle.partitions", str(args.shuffle_partitions))
        .getOrCreate()
    )

    signal = "shuffle spill detected; memory bytes spilled and disk bytes spilled"
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_shuffle_spill_started",
                "run_id": args.run_id,
                "rows": args.rows,
                "keys": args.keys,
                "payload_bytes": args.payload_bytes,
                "shuffle_partitions": args.shuffle_partitions,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )

    data = spark.range(args.rows).selectExpr(
        f"CAST(id % {args.keys} AS STRING) AS shuffle_key",
        f"repeat('x', {args.payload_bytes}) AS payload",
    )
    summary = data.repartition(args.shuffle_partitions, "shuffle_key").groupBy("shuffle_key").agg(
        count("*").alias("row_count")
    )
    summary.write.mode("overwrite").json(args.output.rstrip("/"))

    print(signal)
    raise RuntimeError(signal)


if __name__ == "__main__":
    main()
