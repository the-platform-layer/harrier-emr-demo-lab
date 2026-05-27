# Expected Findings

Expected finding JSON files live in `expected-findings/`.

The scenario validation harness compares Harrier's actual root cause category to the expected category for each scenario.

DB performance scenarios should also assert `recommendation_type=DB` and `pr_ready=true` when Harrier can produce a reviewed SQL or Spark-code remediation.
