#!/usr/bin/env python3
"""Livy session failure scenario for client-mode log layout demos."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--session-id", default="demo-livy-session")
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-livy-session-failure-{args.run_id}"
    ).getOrCreate()

    signal = f"Livy session failed while starting Spark batch for {args.session_id}"
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_livy_session_failure_started",
                "run_id": args.run_id,
                "session_id": args.session_id,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )
    spark.stop()
    raise RuntimeError(signal)


if __name__ == "__main__":
    main()
