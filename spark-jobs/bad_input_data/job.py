#!/usr/bin/env python3
"""Bad input data scenario for Harrier demos."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col, to_timestamp

    args = parse_args()
    spark = (
        SparkSession.builder.appName(f"harrier-demo-bad-input-data-{args.run_id}")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )

    signal = "CSV malformed; schema mismatch with corrupt record"
    print(
        json.dumps(
            {
                "event": "harrier_demo_bad_input_data_started",
                "run_id": args.run_id,
                "input": args.input,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )

    raw = spark.read.option("header", "true").csv(args.input)
    parsed = raw.withColumn("amount_double", col("amount").cast("double")).withColumn(
        "event_timestamp",
        to_timestamp(col("event_ts"), "yyyy-MM-dd'T'HH:mm:ssX"),
    )
    bad_records = parsed.filter(col("amount_double").isNull() | col("event_timestamp").isNull())
    bad_count = bad_records.count()

    if bad_count > 0:
        print(signal)
        print(
            json.dumps(
                {
                    "event": "harrier_demo_bad_input_data_detected",
                    "run_id": args.run_id,
                    "bad_record_count": bad_count,
                    "log_signal": signal,
                },
                sort_keys=True,
            )
        )
        bad_records.show(truncate=False)
        raise ValueError(signal)

    parsed.write.mode("overwrite").parquet(args.output.rstrip("/"))
    spark.stop()


if __name__ == "__main__":
    main()
