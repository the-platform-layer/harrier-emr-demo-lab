#!/usr/bin/env python3
"""Unrecognized terminal failure scenario for Harrier UNKNOWN handling."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--sentinel", default="BLUE-QUARTZ-17")
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-unknown-failure-{args.run_id}"
    ).getOrCreate()

    signal = (
        f"HarrierUnclassifiedDemoSignal sentinel={args.sentinel}; "
        "the job reached a deliberately unmapped terminal condition"
    )

    try:
        print(signal)
        print(
            json.dumps(
                {
                    "event": "harrier_demo_unknown_failure",
                    "run_id": args.run_id,
                    "sentinel": args.sentinel,
                    "log_signal": signal,
                },
                sort_keys=True,
            )
        )
        raise RuntimeError(signal)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
