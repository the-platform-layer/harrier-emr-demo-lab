#!/usr/bin/env python3
"""DB bad SQL plan scenario with read-only EXPLAIN-style evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--query-name", default="demo_orders_customer_join")
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-db-bad-sql-plan-{args.run_id}"
    ).getOrCreate()

    explain = {
        "Plan": {
            "Node Type": "Nested Loop",
            "Join Type": "Inner",
            "Plans": [
                {"Node Type": "Seq Scan", "Relation Name": "demo_orders", "Plan Rows": 5000000},
                {"Node Type": "Seq Scan", "Relation Name": "demo_customers", "Plan Rows": 250000},
            ],
        }
    }
    signal = "EXPLAIN JSON shows sequential scan and nested loop bad join order"
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_db_bad_sql_plan_started",
                "run_id": args.run_id,
                "query_name": args.query_name,
                "explain_format": "json",
                "plan": explain,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )
    spark.stop()
    raise RuntimeError(signal)


if __name__ == "__main__":
    main()
