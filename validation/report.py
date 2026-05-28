"""Write and print scenario validation reports."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation.compare import ComparisonResult


def format_report(result: ComparisonResult) -> dict[str, Any]:
    """Return a JSON-serializable validation report dict."""
    return {
        "scenario": result.scenario,
        "investigation_id": result.investigation_id,
        "outcome": result.outcome,
        "summary": result.summary,
        "validation_timestamp": (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        ),
        "checks": [
            {
                "name": c.name,
                "passed": c.passed,
                "expected": c.expected,
                "actual": c.actual,
                "message": c.message,
            }
            for c in result.checks
        ],
        "root_cause": result.root_cause,
        "recommendations": result.recommendations,
    }


def write_report(result: ComparisonResult, output_path: Path) -> None:
    """Serialize result to output_path (JSON) and print a summary to stdout."""
    report = format_report(result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print_summary(result, str(output_path))


def print_summary(result: ComparisonResult, report_path: str = "") -> None:
    """Print a human-readable one-page summary to stdout."""
    icon = "PASS" if result.outcome == "pass" else "FAIL"
    print(f"\n[{icon}] Scenario: {result.scenario}")
    print(f"  Investigation : {result.investigation_id}")
    print(f"  {result.summary}")
    for check in result.checks:
        status = "PASS" if check.passed else "FAIL"
        line = f"    [{status}] {check.name}"
        line += f"  expected={check.expected!r}  actual={check.actual!r}"
        print(line)
        if check.message:
            print(f"           {check.message}", file=sys.stderr)
    if report_path:
        print(f"  Report written: {report_path}")
    print()
