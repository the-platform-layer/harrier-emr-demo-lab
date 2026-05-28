#!/usr/bin/env python3
"""DB large join spill scenario for Spark and SQL diagnostics."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--fact-rows", type=int, default=100000)
    parser.add_argument("--dim-rows", type=int, default=20000)
    parser.add_argument("--join-keys", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import count

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-db-large-join-spill-{args.run_id}"
    ).getOrCreate()

    signal = "Large join caused hash join spill to temp file and work_mem pressure"
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_db_large_join_spill_started",
                "run_id": args.run_id,
                "fact_rows": args.fact_rows,
                "dim_rows": args.dim_rows,
                "join_keys": args.join_keys,
                "db_plan_summary": "hash join spill to temp file; missing join-key index",
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )

    fact = spark.range(args.fact_rows).selectExpr(
        f"CAST(id % {args.join_keys} AS INT) AS join_key",
        "id AS fact_id",
    )
    dim = spark.range(args.dim_rows).selectExpr(
        f"CAST(id % {args.join_keys} AS INT) AS join_key",
        "id AS dim_id",
    )
    joined = fact.join(dim, "join_key").groupBy("join_key").agg(count("*").alias("join_rows"))
    joined.write.mode("overwrite").json(args.output.rstrip("/"))

    print(signal)
    raise RuntimeError(signal)


if __name__ == "__main__":
    main()
