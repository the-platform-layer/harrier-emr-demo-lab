#!/usr/bin/env python3
"""Database lock timeout scenario for Spark/JDBC troubleshooting."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--relation", default="demo_orders")
    parser.add_argument("--lock-seconds", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-db-lock-timeout-{args.run_id}"
    ).getOrCreate()

    signal = (
        f"PostgreSQL lock timeout waiting for lock on relation {args.relation}; "
        f"blocked by pid after {args.lock_seconds} seconds"
    )
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_db_lock_timeout_started",
                "run_id": args.run_id,
                "relation": args.relation,
                "lock_seconds": args.lock_seconds,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )
    spark.stop()
    raise TimeoutError(signal)


if __name__ == "__main__":
    main()
