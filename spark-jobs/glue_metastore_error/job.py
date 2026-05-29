#!/usr/bin/env python3
"""Glue Data Catalog / Hive metastore table-not-found scenario for Harrier demos."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--database", default="harrier_demo_nonexistent_db")
    parser.add_argument("--table", default="nonexistent_table")
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession

    args = parse_args()
    table_ref = f"{args.database}.{args.table}"

    spark = SparkSession.builder.appName(
        f"harrier-demo-glue-metastore-error-{args.run_id}"
    ).getOrCreate()

    signal = (
        f"GlueMetastoreError: Table or view not found: {table_ref}; "
        f"EntityNotFoundException: Table {args.table} not found in database "
        f"{args.database} in Glue Data Catalog"
    )

    try:
        spark.table(table_ref).count()
    except Exception:
        print(signal)
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
