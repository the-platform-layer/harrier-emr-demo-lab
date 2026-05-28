#!/usr/bin/env python3
"""HDFS/local storage pressure scenario for Harrier demos."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--local-dir", default="/mnt/var/lib/hadoop/tmp/harrier-demo-full")
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession

    args = parse_args()
    spark = SparkSession.builder.appName(f"harrier-demo-hdfs-full-{args.run_id}").getOrCreate()

    signal = f"No space left on device in HDFS; local dirs are full at {args.local_dir}"
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_hdfs_full_started",
                "run_id": args.run_id,
                "local_dir": args.local_dir,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )
    spark.stop()
    raise OSError(signal)


if __name__ == "__main__":
    main()
