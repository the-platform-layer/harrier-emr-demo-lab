#!/usr/bin/env python3
"""Driver-side result collection memory scenario for Harrier demos."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--rows", type=int, default=25000)
    parser.add_argument("--payload-bytes", type=int, default=2048)
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession

    args = parse_args()
    spark = SparkSession.builder.appName(f"harrier-demo-driver-oom-{args.run_id}").getOrCreate()

    signal = "driver java.lang.OutOfMemoryError: Java heap space from collect() result pattern"
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_driver_oom_started",
                "run_id": args.run_id,
                "rows": args.rows,
                "payload_bytes": args.payload_bytes,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )

    payload = spark.range(args.rows).selectExpr(
        f"CAST(id AS STRING) AS row_id",
        f"repeat(CAST(id AS STRING), {args.payload_bytes}) AS oversized_payload",
    )

    try:
        payload.collect()
    except Exception:
        print(signal)
        raise

    raise RuntimeError(signal)


if __name__ == "__main__":
    main()
