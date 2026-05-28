"""Compare Harrier's actual investigation result against expected findings.

``compare(expected, actual)`` is the single entry point.  It accepts the dict
from ``expected-findings/<scenario>.json`` and the dict returned by the MCP
tool ``harrier_start_emr_investigation``, then runs a fixed set of checks and
returns a ``ComparisonResult``.

Checks performed:
  - root_cause_category (or no_false_positive for happy_path)
  - recommendation_type  (when expected JSON contains recommendation_type)
  - pr_ready             (when expected JSON contains pr_ready)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ValidationCheck:
    name: str
    passed: bool
    expected: Any
    actual: Any
    message: str = ""


@dataclass
class ComparisonResult:
    scenario: str
    investigation_id: str
    outcome: Literal["pass", "fail"]
    checks: list[ValidationCheck]
    root_cause: dict[str, Any]
    recommendations: list[dict[str, Any]]
    summary: str


def compare(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> ComparisonResult:
    """Return a ComparisonResult comparing Harrier output to expected findings.

    ``actual`` is the dict returned by ``harrier_start_emr_investigation``.
    ``expected`` is the contents of ``expected-findings/<scenario>.json``.
    """
    scenario = expected.get("scenario", "unknown")
    investigation_id = actual.get("investigation_id", "")
    root_cause = actual.get("root_cause") or {}
    actual_category: str = root_cause.get("category", "UNKNOWN")
    recs: list[dict[str, Any]] = [
        r for r in (actual.get("recommendations") or []) if isinstance(r, dict)
    ]

    checks: list[ValidationCheck] = []

    # ------------------------------------------------------------------
    # 1. Root-cause category (or no-false-positive for happy_path)
    # ------------------------------------------------------------------
    expected_category: str | None = expected.get("expected_root_cause_category")
    if expected_category is None:
        # happy_path: expect no meaningful root cause
        passed = actual_category == "UNKNOWN"
        checks.append(ValidationCheck(
            name="no_false_positive",
            passed=passed,
            expected="UNKNOWN",
            actual=actual_category,
            message=(
                ""
                if passed
                else f"Expected no root cause (UNKNOWN) but Harrier returned {actual_category!r}"
            ),
        ))
    else:
        acceptable_extra: set[str] = set(
            expected.get("acceptable_related_categories") or []
        )
        acceptable = {expected_category} | acceptable_extra
        passed = actual_category in acceptable
        checks.append(ValidationCheck(
            name="root_cause_category",
            passed=passed,
            expected=expected_category,
            actual=actual_category,
            message=(
                ""
                if passed
                else (
                    f"Expected {expected_category!r}"
                    + (f" (or {sorted(acceptable_extra)!r})" if acceptable_extra else "")
                    + f", got {actual_category!r}"
                )
            ),
        ))

    # ------------------------------------------------------------------
    # 2. Recommendation type
    # ------------------------------------------------------------------
    expected_rec_type: str | None = expected.get("recommendation_type")
    if expected_rec_type is not None:
        actual_rec_types = [r.get("type") for r in recs]
        passed = expected_rec_type in actual_rec_types
        checks.append(ValidationCheck(
            name="recommendation_type",
            passed=passed,
            expected=expected_rec_type,
            actual=actual_rec_types,
            message=(
                ""
                if passed
                else f"Expected recommendation type {expected_rec_type!r}, got {actual_rec_types!r}"
            ),
        ))

    # ------------------------------------------------------------------
    # 3. PR-ready flag
    # ------------------------------------------------------------------
    expected_pr_ready: bool | None = expected.get("pr_ready")
    if expected_pr_ready is not None:
        actual_pr_ready = any(r.get("pr_ready") for r in recs)
        passed = actual_pr_ready == expected_pr_ready
        checks.append(ValidationCheck(
            name="pr_ready",
            passed=passed,
            expected=expected_pr_ready,
            actual=actual_pr_ready,
            message=(
                ""
                if passed
                else f"Expected pr_ready={expected_pr_ready}, got {actual_pr_ready}"
            ),
        ))

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------
    all_passed = all(c.passed for c in checks)
    outcome: Literal["pass", "fail"] = "pass" if all_passed else "fail"
    failed_names = [c.name for c in checks if not c.passed]
    summary = (
        f"PASS: all {len(checks)} check(s) passed"
        if all_passed
        else f"FAIL: {len(failed_names)} of {len(checks)} check(s) failed: {', '.join(failed_names)}"
    )

    return ComparisonResult(
        scenario=scenario,
        investigation_id=investigation_id,
        outcome=outcome,
        checks=checks,
        root_cause=root_cause,
        recommendations=recs,
        summary=summary,
    )
