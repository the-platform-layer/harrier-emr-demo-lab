# Expected Findings

Expected finding JSON files live in `expected-findings/`.

The scenario validation harness compares Harrier's actual root cause category to the expected category for each scenario.

DB performance scenarios should also assert `recommendation_type=DB` and `pr_ready=true` when Harrier can produce a reviewed SQL or Spark-code remediation.

The `db_bad_sql_plan` scenario should assert that Harrier uses SQL plan evidence, not only Spark runtime symptoms, before returning `DB_BAD_SQL_PLAN`.
