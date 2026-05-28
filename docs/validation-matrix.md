# Harrier Demo Validation Matrix

Last updated: 2026-05-28

This matrix tracks the currently stable demo scenarios that have been validated against the deployed Harrier MCP endpoint.

| Scenario | Last Run Time (UTC) | Expected Category | Actual Category | Result | Report Path | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `happy_path` | 2026-05-28T13:49:26Z | `UNKNOWN` | `UNKNOWN` | Pass | `.harrier-demo/validation/happy_path-20260528T134926Z.json` | No false positive on a successful Spark job. |
| `executor_oom` | 2026-05-28T13:49:44Z | `EXECUTOR_OOM` | `EXECUTOR_OOM` | Pass | `.harrier-demo/validation/executor_oom-20260528T134944Z.json` | Validates cluster-mode container log discovery and Spark config recommendations. |
| `driver_oom` | 2026-05-28T13:49:38Z | `DRIVER_OOM` | `DRIVER_OOM` | Pass | `.harrier-demo/validation/driver_oom-20260528T134938Z.json` | Produces Spark config and code recommendations with PR-ready output. |
| `missing_dependency` | 2026-05-28T13:49:26Z | `DEPENDENCY_MISSING` | `DEPENDENCY_MISSING` | Pass | `.harrier-demo/validation/missing_dependency-20260528T134926Z.json` | Client-mode dependency signal was read from step stdout/stderr. |
| `s3_access_denied` | 2026-05-28T13:49:44Z | `S3_ACCESS_DENIED` | `S3_ACCESS_DENIED` | Pass | `.harrier-demo/validation/s3_access_denied-20260528T134944Z.json` | Requires cluster-mode YARN container logs; validator waits for those logs. |
| `bad_input_data` | 2026-05-28T13:49:44Z | `BAD_INPUT_DATA` | `BAD_INPUT_DATA` | Pass | `.harrier-demo/validation/bad_input_data-20260528T134944Z.json` | Requires cluster-mode YARN container logs; produced code and runbook recommendations. |
| `db_bad_sql_plan` | 2026-05-28T13:49:44Z | `DB_BAD_SQL_PLAN` | `DB_BAD_SQL_PLAN` | Pass | `.harrier-demo/validation/db_bad_sql_plan-20260528T134944Z.json` | First DB/SQL demo; validates SQL plan evidence and DB recommendation output. |
| `db_partition_hotspot` | 2026-05-28T13:49:44Z | `DB_PARTITION_HOTSPOT` | `DB_PARTITION_HOTSPOT` | Pass | `.harrier-demo/validation/db_partition_hotspot-20260528T134944Z.json` | DB partitioning demo with PR-ready database recommendation output. |
| `kms_access_denied` | 2026-05-28T13:49:44Z | `KMS_ACCESS_DENIED` | `KMS_ACCESS_DENIED` | Pass | `.harrier-demo/validation/kms_access_denied-20260528T134944Z.json` | KMS decrypt denial is classified separately from generic S3 access failures. |
| `data_skew` | 2026-05-28T13:49:44Z | `DATA_SKEW` | `DATA_SKEW` | Pass | `.harrier-demo/validation/data_skew-20260528T134944Z.json` | Validates hot-partition evidence without false S3 path classification. |
| `shuffle_spill` | 2026-05-28T13:49:44Z | `SHUFFLE_SPILL` | `SHUFFLE_SPILL` | Pass | `.harrier-demo/validation/shuffle_spill-20260528T134944Z.json` | Validates shuffle spill signals from Spark/YARN logs. |
| `hdfs_full` | 2026-05-28T13:49:44Z | `HDFS_FULL` | `HDFS_FULL` | Pass | `.harrier-demo/validation/hdfs_full-20260528T134944Z.json` | Operational cluster/storage recommendation; no PR-ready change expected. |
| `db_connection_failure` | 2026-05-28T13:49:38Z | `DB_CONNECTION_FAILURE` | `DB_CONNECTION_FAILURE` | Pass | `.harrier-demo/validation/db_connection_failure-20260528T134938Z.json` | Client-mode DB connectivity issue; returns DB/runbook guidance without PR-ready output. |
| `db_lock_timeout` | 2026-05-28T13:49:26Z | `DB_LOCK_TIMEOUT` | `DB_LOCK_TIMEOUT` | Pass | `.harrier-demo/validation/db_lock_timeout-20260528T134926Z.json` | DB lock wait issue; operational recommendation remains non-PR-ready. |
| `db_large_join_spill` | 2026-05-28T13:49:44Z | `DB_LARGE_JOIN_SPILL` | `DB_LARGE_JOIN_SPILL` | Pass | `.harrier-demo/validation/db_large_join_spill-20260528T134944Z.json` | Large join/spill DB demo with PR-ready SQL recommendation output. |
| `livy_session_failure` | 2026-05-28T13:49:38Z | `LIVY_SESSION_FAILURE` | `LIVY_SESSION_FAILURE` | Pass | `.harrier-demo/validation/livy_session_failure-20260528T134938Z.json` | Client-mode Livy startup/session failure; runbook/cluster guidance is not PR-ready. |

## Operational Notes

- Use `scripts/validate_demo_suite.sh` to rerun the stable suite. Set `VALIDATE_PARALLEL=1` to validate the suite concurrently.
- The validator waits for EMR S3 log archival before calling Harrier. This is important for cluster-mode jobs because the actionable Python exception usually lands in YARN container logs after the EMR step is already terminal.
- Set `NO_LOG_WAIT=1` only when intentionally testing partial-log behavior.
