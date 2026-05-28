#!/usr/bin/env python3
"""Database connection failure scenario for Spark/JDBC troubleshooting."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument(
        "--jdbc-url",
        default="jdbc:postgresql://harrier-demo-unreachable.invalid:5432/harrier_demo",
    )
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-db-connection-failure-{args.run_id}"
    ).getOrCreate()

    signal = f"PSQLException JDBC connection refused for database host in {args.jdbc_url}"
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_db_connection_failure_started",
                "run_id": args.run_id,
                "jdbc_url": args.jdbc_url,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )
    spark.stop()
    raise ConnectionError(signal)


if __name__ == "__main__":
    main()
