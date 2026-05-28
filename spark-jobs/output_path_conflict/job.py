#!/usr/bin/env python3
"""Output path already exists (commit failure) scenario for Harrier demos."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-output-path-conflict-{args.run_id}"
    ).getOrCreate()

    signal = (
        f"path {args.output} already exists; "
        "AnalysisException output path already exists. "
        "Set mode as overwrite to overwrite the existing path."
    )

    try:
        # Phase 1: write succeeds (seeds the output path)
        spark.range(5).write.mode("overwrite").parquet(args.output)

        # Phase 2: write to same path with ErrorIfExists (default) — raises AnalysisException
        print(signal)
        print(
            json.dumps(
                {
                    "event": "harrier_demo_output_path_conflict_started",
                    "run_id": args.run_id,
                    "output": args.output,
                    "log_signal": signal,
                },
                sort_keys=True,
            )
        )
        spark.range(5).write.parquet(args.output)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
