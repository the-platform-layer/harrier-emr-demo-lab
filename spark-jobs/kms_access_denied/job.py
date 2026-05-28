#!/usr/bin/env python3
"""KMS AccessDenied scenario for encrypted S3 data."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--encrypted-input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--key-arn", default="arn:aws:kms:ap-southeast-2:111122223333:key/demo-denied")
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-kms-access-denied-{args.run_id}"
    ).getOrCreate()

    signal = (
        f"AccessDeniedException calling kms:Decrypt for encrypted S3 data "
        f"{args.encrypted_input} using KMS key {args.key_arn}"
    )
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_kms_access_denied_started",
                "run_id": args.run_id,
                "encrypted_input": args.encrypted_input,
                "key_arn": args.key_arn,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )
    spark.stop()
    raise PermissionError(signal)


if __name__ == "__main__":
    main()
