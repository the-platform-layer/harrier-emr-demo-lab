#!/usr/bin/env python3
"""S3 path missing (NoSuchKey) scenario for Harrier demos."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--missing-input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-s3-path-missing-{args.run_id}"
    ).getOrCreate()

    signal = f"NoSuchKey: The specified key does not exist at {args.missing_input}"
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_s3_path_missing_started",
                "run_id": args.run_id,
                "missing_input": args.missing_input,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )

    try:
        spark.read.parquet(args.missing_input).count()
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
