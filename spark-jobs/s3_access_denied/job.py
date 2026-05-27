#!/usr/bin/env python3
"""S3 AccessDenied scenario for Harrier demos."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--denied-input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument(
        "--attempt-read",
        action="store_true",
        help="Attempt the S3 read before raising. Use only with a demo-only denied prefix.",
    )
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-s3-access-denied-{args.run_id}"
    ).getOrCreate()

    signal = f"AccessDenied while reading {args.denied_input}"
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_s3_access_denied_started",
                "run_id": args.run_id,
                "denied_input": args.denied_input,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )

    try:
        if args.attempt_read:
            spark.read.text(args.denied_input).count()
        raise PermissionError(
            f"{signal}; Amazon S3 returned 403 Forbidden for bucket/key in demo path"
        )
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
