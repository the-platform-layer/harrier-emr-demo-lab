#!/usr/bin/env python3
"""Missing Python dependency scenario for Harrier demos."""

from __future__ import annotations

import argparse
import importlib
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--module", default="harrier_demo_missing_dependency")
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-missing-dependency-{args.run_id}"
    ).getOrCreate()

    signal = f"ModuleNotFoundError: No module named {args.module}"
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_missing_dependency_started",
                "run_id": args.run_id,
                "missing_module": args.module,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )

    try:
        importlib.import_module(args.module)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
