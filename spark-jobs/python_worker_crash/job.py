#!/usr/bin/env python3
"""Python worker crash / UDF serialization failure scenario for Harrier demos."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--partitions", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import udf
    from pyspark.sql.types import IntegerType

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-python-worker-crash-{args.run_id}"
    ).getOrCreate()

    signal = (
        "An exception was thrown from the Python worker. "
        "Python worker process exited unexpectedly (crashed). "
        "PythonException: unhandled exception in Python UDF executor task"
    )
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_python_worker_crash_started",
                "run_id": args.run_id,
                "partitions": args.partitions,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )

    # UDF raises an error that PySpark wraps in PythonException — the wrapper
    # text "An exception was thrown from the Python worker" appears in driver logs.
    def crashing_udf(x):
        raise RuntimeError(
            "Python worker process exited unexpectedly (crashed); "
            "PythonException unhandled exception in Python UDF executor task"
        )

    crash = udf(crashing_udf, IntegerType())

    try:
        spark.range(args.partitions).withColumn("result", crash("id")).collect()
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
