#!/usr/bin/env python3
"""Safe DB lock timeout simulator for demo planning.

This helper does not connect to a database. It prints the exact diagnostic
shape used by the Spark `db_lock_timeout` scenario so operators can rehearse
the evidence without holding a real lock.
"""

from __future__ import annotations

import argparse
import json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--relation", default="demo_orders")
    parser.add_argument("--blocked-pid", default="4242")
    parser.add_argument("--wait-seconds", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    signal = (
        f"PostgreSQL lock timeout waiting for lock on relation {args.relation}; "
        f"blocked by pid {args.blocked_pid} after {args.wait_seconds} seconds"
    )
    print(
        json.dumps(
            {
                "event": "harrier_demo_db_lock_timeout_simulated",
                "relation": args.relation,
                "blocked_pid": args.blocked_pid,
                "wait_seconds": args.wait_seconds,
                "log_signal": signal,
            },
            sort_keys=True,
        )
    )
    print(signal)


if __name__ == "__main__":
    main()
