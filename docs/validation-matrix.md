# Harrier Demo Validation Matrix

Last updated: 2026-05-29

This matrix tracks the currently stable demo scenarios that have been validated against the deployed Harrier MCP endpoint.

| Scenario | Last Run Time (UTC) | Expected Category | Actual Category | Result | Report Path | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `happy_path` | 2026-05-29T00:48:05Z | `UNKNOWN` | `UNKNOWN` | Pass | `.harrier-demo/validation/happy_path-20260529T004805Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`; no false positive on successful Spark job. |
| `executor_oom` | 2026-05-29T00:43:26Z | `EXECUTOR_OOM` | `EXECUTOR_OOM` | Pass | `.harrier-demo/validation/executor_oom-20260529T004326Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `driver_oom` | 2026-05-29T00:38:05Z | `DRIVER_OOM` | `DRIVER_OOM` | Pass | `.harrier-demo/validation/driver_oom-20260529T003805Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `missing_dependency` | 2026-05-29T00:43:13Z | `DEPENDENCY_MISSING` | `DEPENDENCY_MISSING` | Pass | `.harrier-demo/validation/missing_dependency-20260529T004313Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `s3_access_denied` | 2026-05-29T00:43:21Z | `S3_ACCESS_DENIED` | `S3_ACCESS_DENIED` | Pass | `.harrier-demo/validation/s3_access_denied-20260529T004321Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `bad_input_data` | 2026-05-29T00:53:37Z | `BAD_INPUT_DATA` | `BAD_INPUT_DATA` | Pass | `.harrier-demo/validation/bad_input_data-20260529T005337Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `db_bad_sql_plan` | 2026-05-29T00:48:12Z | `DB_BAD_SQL_PLAN` | `DB_BAD_SQL_PLAN` | Pass | `.harrier-demo/validation/db_bad_sql_plan-20260529T004812Z.json` | Fresh DB/SQL plan demo on cluster `j-4UGD4SUAIWMR`. |
| `db_partition_hotspot` | 2026-05-29T00:43:10Z | `DB_PARTITION_HOTSPOT` | `DB_PARTITION_HOTSPOT` | Pass | `.harrier-demo/validation/db_partition_hotspot-20260529T004310Z.json` | Fresh DB partitioning demo on cluster `j-4UGD4SUAIWMR`. |
| `kms_access_denied` | 2026-05-29T00:48:08Z | `KMS_ACCESS_DENIED` | `KMS_ACCESS_DENIED` | Pass | `.harrier-demo/validation/kms_access_denied-20260529T004808Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `data_skew` | 2026-05-29T00:48:32Z | `DATA_SKEW` | `DATA_SKEW` | Pass | `.harrier-demo/validation/data_skew-20260529T004832Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `shuffle_spill` | 2026-05-29T00:43:15Z | `SHUFFLE_SPILL` | `SHUFFLE_SPILL` | Pass | `.harrier-demo/validation/shuffle_spill-20260529T004315Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `hdfs_full` | 2026-05-29T00:43:12Z | `HDFS_FULL` | `HDFS_FULL` | Pass | `.harrier-demo/validation/hdfs_full-20260529T004312Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `db_connection_failure` | 2026-05-29T00:48:28Z | `DB_CONNECTION_FAILURE` | `DB_CONNECTION_FAILURE` | Pass | `.harrier-demo/validation/db_connection_failure-20260529T004828Z.json` | Fresh DB connectivity demo on cluster `j-4UGD4SUAIWMR`. |
| `db_lock_timeout` | 2026-05-29T00:43:16Z | `DB_LOCK_TIMEOUT` | `DB_LOCK_TIMEOUT` | Pass | `.harrier-demo/validation/db_lock_timeout-20260529T004316Z.json` | Fresh DB lock demo on cluster `j-4UGD4SUAIWMR`. |
| `db_large_join_spill` | 2026-05-29T00:48:27Z | `DB_LARGE_JOIN_SPILL` | `DB_LARGE_JOIN_SPILL` | Pass | `.harrier-demo/validation/db_large_join_spill-20260529T004827Z.json` | Fresh DB large join/spill demo on cluster `j-4UGD4SUAIWMR`. |
| `glue_metastore_error` | 2026-05-29T02:58:58Z | `METASTORE_ERROR` | `METASTORE_ERROR` | Pass | `.harrier-demo/validation/glue_metastore_error-20260529T025858Z.json` | Fresh Glue Data Catalog missing table demo on cluster `j-4UGD4SUAIWMR`; verifies runbook plus code recommendation. |
| `livy_session_failure` | 2026-05-29T00:48:20Z | `LIVY_SESSION_FAILURE` | `LIVY_SESSION_FAILURE` | Pass | `.harrier-demo/validation/livy_session_failure-20260529T004820Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `s3_path_missing` | 2026-05-29T00:53:07Z | `S3_PATH_MISSING` | `S3_PATH_MISSING` | Pass | `.harrier-demo/validation/s3_path_missing-20260529T005307Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `output_path_conflict` | 2026-05-29T00:48:23Z | `OUTPUT_PATH_CONFLICT` | `OUTPUT_PATH_CONFLICT` | Pass | `.harrier-demo/validation/output_path_conflict-20260529T004823Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `schema_mismatch` | 2026-05-29T00:48:30Z | `BAD_INPUT_DATA` | `BAD_INPUT_DATA` | Pass | `.harrier-demo/validation/schema_mismatch-20260529T004830Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `python_worker_crash` | 2026-05-29T00:43:23Z | `PYTHON_WORKER_CRASH` | `PYTHON_WORKER_CRASH` | Pass | `.harrier-demo/validation/python_worker_crash-20260529T004323Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |
| `unknown_failure` | 2026-05-29T02:23:56Z | `UNKNOWN` | `UNKNOWN` | Pass | `.harrier-demo/validation/unknown_failure-20260529T022356Z.json` | Unknown-failure safety scenario; verifies runbook-only recommendations and no PR-ready fix. |
| `spot_interruption` | 2026-05-29T00:33:17Z | `EXECUTOR_LOST` | `EXECUTOR_LOST` | Pass | `.harrier-demo/validation/spot_interruption-20260529T003317Z.json` | Fresh run on cluster `j-4UGD4SUAIWMR`. |

## Operational Notes

- Use `scripts/validate_demo_suite.sh` to rerun the stable suite. Set `VALIDATE_PARALLEL=1` to validate the suite concurrently.
- The validator waits for EMR S3 log archival before calling Harrier. This is important for cluster-mode jobs because the actionable Python exception usually lands in YARN container logs after the EMR step is already terminal.
- Set `NO_LOG_WAIT=1` only when intentionally testing partial-log behavior.
