# Harrier Demo Validation Matrix

Last updated: 2026-05-28

This matrix tracks the currently stable demo scenarios that have been validated against the deployed Harrier MCP endpoint.

| Scenario | Last Run Time (UTC) | Expected Category | Actual Category | Result | Report Path | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `happy_path` | 2026-05-28T12:17:25Z | `UNKNOWN` | `UNKNOWN` | Pass | `.harrier-demo/validation/happy_path-20260528T121725Z.json` | No false positive on a successful Spark job. |
| `executor_oom` | 2026-05-28T12:17:38Z | `EXECUTOR_OOM` | `EXECUTOR_OOM` | Pass | `.harrier-demo/validation/executor_oom-20260528T121738Z.json` | Validates cluster-mode container log discovery and Spark config recommendations. |
| `driver_oom` | 2026-05-28T12:17:50Z | `DRIVER_OOM` | `DRIVER_OOM` | Pass | `.harrier-demo/validation/driver_oom-20260528T121750Z.json` | Produces Spark config and code recommendations with PR-ready output. |
| `missing_dependency` | 2026-05-28T12:18:02Z | `DEPENDENCY_MISSING` | `DEPENDENCY_MISSING` | Pass | `.harrier-demo/validation/missing_dependency-20260528T121802Z.json` | Client-mode dependency signal was read from step stdout/stderr. |
| `s3_access_denied` | 2026-05-28T12:18:15Z | `S3_ACCESS_DENIED` | `S3_ACCESS_DENIED` | Pass | `.harrier-demo/validation/s3_access_denied-20260528T121815Z.json` | Requires cluster-mode YARN container logs; validator waits for those logs. |
| `bad_input_data` | 2026-05-28T12:18:29Z | `BAD_INPUT_DATA` | `BAD_INPUT_DATA` | Pass | `.harrier-demo/validation/bad_input_data-20260528T121829Z.json` | Requires cluster-mode YARN container logs; produced code and runbook recommendations. |
| `db_bad_sql_plan` | 2026-05-28T12:44:20Z | `DB_BAD_SQL_PLAN` | `DB_BAD_SQL_PLAN` | Pass | `.harrier-demo/validation/db_bad_sql_plan-20260528T124420Z.json` | First DB/SQL demo; validates SQL plan evidence and DB recommendation output. |

## Operational Notes

- Use `scripts/validate_demo_suite.sh` to rerun the stable suite.
- The validator waits for EMR S3 log archival before calling Harrier. This is important for cluster-mode jobs because the actionable Python exception usually lands in YARN container logs after the EMR step is already terminal.
- Set `NO_LOG_WAIT=1` only when intentionally testing partial-log behavior.
