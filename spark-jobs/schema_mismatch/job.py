#!/usr/bin/env python3
"""Parquet schema evolution / type mismatch scenario for Harrier demos."""

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
    from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-schema-mismatch-{args.run_id}"
    ).getOrCreate()

    signal = (
        "schema mismatch: cannot cast StringType to DoubleType; "
        "parquet type mismatch in column 'amount' "
        "expected DoubleType but found StringType"
    )

    staging_path = f"{args.output}/_staging"

    try:
        # Phase 1: write Parquet where 'amount' is a String
        write_schema = StructType(
            [
                StructField("id", IntegerType(), nullable=False),
                StructField("amount", StringType(), nullable=True),
            ]
        )
        spark.createDataFrame(
            [(1, "not-a-number"), (2, "also-bad")], schema=write_schema
        ).write.mode("overwrite").parquet(staging_path)

        # Phase 2: read with strict DoubleType schema + FAILFAST → AnalysisException / ClassCastException
        read_schema = StructType(
            [
                StructField("id", IntegerType(), nullable=False),
                StructField("amount", DoubleType(), nullable=False),
            ]
        )
        print(signal)
        print(
            json.dumps(
                {
                    "event": "harrier_demo_schema_mismatch_started",
                    "run_id": args.run_id,
                    "staging_path": staging_path,
                    "log_signal": signal,
                },
                sort_keys=True,
            )
        )
        # Parquet FAILFAST mode is silently ignored for type mismatches; cast and check manually.
        from pyspark.sql.functions import col

        df = spark.read.parquet(staging_path)
        null_count = df.withColumn("_amount_d", col("amount").cast("double")).filter(
            col("_amount_d").isNull()
        ).count()
        if null_count > 0:
            raise ValueError(
                f"schema mismatch: cannot cast StringType to DoubleType in column 'amount'; "
                f"parquet type mismatch: {null_count} row(s) failed cast"
            )
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
