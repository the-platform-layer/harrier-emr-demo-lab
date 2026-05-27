#!/usr/bin/env python3
"""Long-running Spark/JDBC scenario backed by a read-only PostgreSQL delay query."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--sleep-seconds", type=int, default=900)
    parser.add_argument("--query")
    return parser.parse_args()


def load_secret(secret_id: str | None) -> dict[str, str]:
    if not secret_id:
        return {}

    import boto3

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_id)
    secret_string = response.get("SecretString") or "{}"
    parsed = json.loads(secret_string)
    return {str(key): str(value) for key, value in parsed.items() if value is not None}


def main() -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import current_timestamp, lit

    args = parse_args()
    secret = load_secret(os.environ.get("HARRIER_DB_SECRET_ID"))
    jdbc_url = os.environ.get("HARRIER_JDBC_URL") or secret.get("jdbc_url") or secret.get("url")
    user = os.environ.get("HARRIER_DB_USER") or secret.get("username") or secret.get("user")
    password = os.environ.get("HARRIER_DB_PASSWORD") or secret.get("password")

    if not jdbc_url:
        raise ValueError("Missing JDBC URL. Provide HARRIER_JDBC_URL or a secret with jdbc_url/url.")
    if not user:
        raise ValueError("Missing DB user. Provide HARRIER_DB_USER or a secret with username/user.")
    if not password:
        raise ValueError("Missing DB password. Provide a secret with password.")

    query = args.query or (
        f"select 1 as delay_marker from (select pg_sleep({args.sleep_seconds})) harrier_sleep"
    )
    dbtable = f"({query}) harrier_delay"

    spark = SparkSession.builder.appName(
        f"harrier-demo-long-running-db-delay-{args.run_id}"
    ).getOrCreate()
    print(
        json.dumps(
            {
                "event": "harrier_demo_long_running_db_delay_started",
                "run_id": args.run_id,
                "sleep_seconds": args.sleep_seconds,
                "query_shape": "custom" if args.query else "pg_sleep",
            },
            sort_keys=True,
        )
    )

    result = (
        spark.read.format("jdbc")
        .option("url", jdbc_url)
        .option("dbtable", dbtable)
        .option("user", user)
        .option("password", password)
        .option("fetchsize", "1")
        .load()
        .withColumn("run_id", lit(args.run_id))
        .withColumn("processed_at", current_timestamp())
        .cache()
    )
    row_count = result.count()
    result.write.mode("overwrite").json(args.output.rstrip("/"))

    print(
        json.dumps(
            {
                "event": "harrier_demo_long_running_db_delay_complete",
                "run_id": args.run_id,
                "output": args.output.rstrip("/"),
                "rows": row_count,
            },
            sort_keys=True,
        )
    )
    spark.stop()


if __name__ == "__main__":
    main()
