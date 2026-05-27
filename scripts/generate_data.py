#!/usr/bin/env python3
"""Generate deterministic CSV input data for the happy path Spark demo."""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


DEFAULT_OUTPUT = Path("sample-data/generated/happy_path/events.csv")
EVENT_TYPES = ("view", "cart", "purchase", "refund")
COUNTRIES = ("AU", "US", "GB", "IN", "SG")


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=positive_int, default=1000)
    parser.add_argument("--seed", type=int, default=20260527)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def iter_rows(row_count: int, seed: int):
    rng = random.Random(seed)
    base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    for idx in range(1, row_count + 1):
        event_type = rng.choices(EVENT_TYPES, weights=(52, 25, 20, 3), k=1)[0]
        amount = 0.0
        if event_type == "cart":
            amount = round(rng.uniform(10, 250), 2)
        elif event_type == "purchase":
            amount = round(rng.uniform(15, 500), 2)
        elif event_type == "refund":
            amount = round(-rng.uniform(5, 200), 2)

        event_ts = base + timedelta(minutes=rng.randint(0, 60 * 24 * 14))
        yield {
            "event_id": f"evt-{idx:08d}",
            "customer_id": f"cust-{rng.randint(1, max(20, row_count // 8)):06d}",
            "event_type": event_type,
            "amount": f"{amount:.2f}",
            "event_ts": event_ts.isoformat().replace("+00:00", "Z"),
            "country": rng.choice(COUNTRIES),
        }


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["event_id", "customer_id", "event_type", "amount", "event_ts", "country"]
    event_counts = {event_type: 0 for event_type in EVENT_TYPES}
    country_counts = {country: 0 for country in COUNTRIES}

    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in iter_rows(args.rows, args.seed):
            event_counts[row["event_type"]] += 1
            country_counts[row["country"]] += 1
            writer.writerow(row)

    summary = {
        "output": str(args.output.resolve()),
        "rows": args.rows,
        "seed": args.seed,
        "event_counts": event_counts,
        "country_counts": country_counts,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
