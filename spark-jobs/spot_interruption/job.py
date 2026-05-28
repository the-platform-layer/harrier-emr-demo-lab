#!/usr/bin/env python3
"""Spot interruption / executor lost scenario for Harrier demos."""

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

    args = parse_args()
    spark = SparkSession.builder.appName(
        f"harrier-demo-spot-interruption-{args.run_id}"
    ).getOrCreate()

    signal = (
        "executor lost; container killed by YARN due to node loss; "
        "remote RPC client disassociated from executor"
    )
    print(signal)
    print(
        json.dumps(
            {
                "event": "harrier_demo_spot_interruption_started",
                "run_id": args.run_id,
                "partitions": args.partitions,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )

    def simulate_node_loss(partition_index, rows):
        # Emit the executor-side signal before failing
        print(
            f"executor lost partition={partition_index}; "
            "container killed by YARN due to node loss; "
            "remote rpc client disassociated from executor"
        )
        raise RuntimeError(
            f"executor lost partition={partition_index}; "
            "container killed by YARN due to node loss"
        )
        yield  # pragma: no cover

    try:
        base = spark.sparkContext.parallelize(range(args.partitions), args.partitions)
        base.mapPartitionsWithIndex(simulate_node_loss).collect()
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
