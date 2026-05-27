# Expected Findings

Expected finding JSON files live in `expected-findings/`.

The scenario validation harness compares Harrier's actual root cause category to the expected category for each scenario.

The `happy_path` expected finding is intentionally empty. It is a baseline proof that Harrier can receive context, inspect reachable EMR evidence, and avoid inventing a root cause when the Spark job succeeds.

Slice 10 expected findings cover:

- `executor_oom`
- `driver_oom`
- `missing_dependency`
- `s3_access_denied`
- `bad_input_data`

Each file includes the expected outcome, primary root-cause category, evidence strings Harrier should find, and recommendation type.

Long-running scenarios should be validated before the Spark step fails. They should assert that Harrier returns a delay explanation, current running state, and whether the likely cause is data, resource, or DB-side work.

DB performance scenarios should also assert `recommendation_type=DB` and `pr_ready=true` when Harrier can produce a reviewed SQL or Spark-code remediation.

The `db_bad_sql_plan` scenario should assert that Harrier uses SQL plan evidence, not only Spark runtime symptoms, before returning `DB_BAD_SQL_PLAN`.
