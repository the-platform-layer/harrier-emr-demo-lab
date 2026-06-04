# Scenarios

Every Spark scenario should record the deploy mode used by the run:

```text
client
cluster
```

This matters because driver logs land in different places:

- cluster mode: driver logs are usually YARN/container logs.
- client mode: driver logs are usually step/controller/Livy/primary-node logs.

The stable demo set includes both client-mode and cluster-mode runs so Harrier
can validate the two common EMR log layouts.

Initial scenario set:

- `happy_path`
- `executor_oom`
- `driver_oom`
- `missing_dependency`
- `s3_access_denied`
- `bad_input_data`

## EMR Serverless Scenario Set

The Serverless scenario set covers Spark failures that do not require
EC2-specific cluster or YARN behavior:

```bash
RUNTIME=emr_serverless ./scripts/run_scenario.sh happy_path
RUNTIME=emr_serverless ./scripts/run_scenario.sh executor_oom
RUNTIME=emr_serverless ./scripts/run_scenario.sh missing_dependency
RUNTIME=emr_serverless ./scripts/run_scenario.sh s3_path_missing
RUNTIME=emr_serverless ./scripts/run_scenario.sh bad_input_data
```

The exported context uses the runtime-aware MCP contract:

```json
{
  "runtime": "emr_serverless",
  "target": {
    "serverless_application_id": "00f1abcd2efg3hij",
    "job_run_id": "00f1abcd2efg3hij-000001"
  }
}
```

Serverless logs are published to both S3 and CloudWatch:

- S3: `s3://<logs-bucket>/emr-serverless/applications/<application-id>/jobs/<job-run-id>/...`
- CloudWatch Logs: `/harrier-demo/emr-serverless`, with stream prefix `harrier-demo/<scenario>/<run-id>`

Expected findings are reused from the matching EC2 scenario files because the Spark failure signatures are intentionally the same. The difference is the runtime target and log layout, not the root-cause category.

## EMR On EKS Scenario Set

The EMR on EKS scenario set runs against an existing EKS cluster and namespace:

```bash
RUNTIME=emr_eks ./scripts/run_scenario.sh happy_path
RUNTIME=emr_eks ./scripts/run_scenario.sh executor_oom
RUNTIME=emr_eks ./scripts/run_scenario.sh image_pull_failure
RUNTIME=emr_eks ./scripts/run_scenario.sh pod_pending_resource_pressure
RUNTIME=emr_eks ./scripts/run_scenario.sh s3_access_denied
```

The exported context uses the runtime-aware MCP contract:

```json
{
  "runtime": "emr_eks",
  "target": {
    "virtual_cluster_id": "vc-1234567890abcdef0",
    "job_run_id": "job-run-123",
    "eks_cluster_name": "analytics-dev",
    "namespace": "harrier-emr-jobs"
  }
}
```

EKS logs are published to both S3 and CloudWatch:

- S3: `s3://<logs-bucket>/emr-eks/<virtual-cluster-id>/jobs/<job-run-id>/containers/...`
- CloudWatch Logs: `/harrier-demo/emr-eks`, with stream prefix `harrier-demo/<scenario>/<run-id>`

`happy_path`, `executor_oom`, and `s3_access_denied` reuse the matching Spark scenario expected findings. `image_pull_failure` and `pod_pending_resource_pressure` add EKS-specific expected findings because they are diagnosed primarily from Kubernetes pod status rather than Spark stack traces.

## `happy_path`

Proves the baseline EMR on EC2 environment works before any failure scenario is introduced.

Run:

```bash
./scripts/run_scenario.sh happy_path
```

Expected evidence:

- EMR step is submitted with `spark-submit`.
- Input CSV lands under the raw S3 bucket.
- Processed parquet output lands under the processed S3 bucket.
- Exported context includes region, cluster ID, step ID, deploy mode, job state, and a time window.
- YARN application ID is included when it can be found in archived step logs.

Expected Harrier result:

- No root-cause finding.
- Evidence confirms the cluster, step, S3 paths, and logs are reachable.

## Core Failure Scenarios

Run any batch 1 scenario through the same runner:

```bash
./scripts/run_scenario.sh executor_oom
./scripts/run_scenario.sh driver_oom
./scripts/run_scenario.sh missing_dependency
./scripts/run_scenario.sh s3_access_denied
./scripts/run_scenario.sh bad_input_data
```

`driver_oom` and `missing_dependency` default to client deploy mode so the demo covers client-side driver log layout. `executor_oom`, `s3_access_denied`, and `bad_input_data` default to cluster deploy mode so the demo covers YARN/container log layout. Set `DEPLOY_MODE=client` or `DEPLOY_MODE=cluster` to override either default.

Clean up a run with:

```bash
./scripts/cleanup_scenario.sh <scenario>
```

### `executor_oom`

Simulates executor/container memory pressure with bounded allocation defaults and a classifier-friendly YARN memory signal.

Expected evidence:

- Executor or container logs include `java.lang.OutOfMemoryError` and YARN physical-memory wording.
- Run context diagnostic signals identify `EXECUTOR_OOM`.

Expected recommendation:

- Tune executor memory, memory overhead, cores, partition size, cache use, and wide transformations.

### `driver_oom`

Simulates driver-side memory pressure from collecting an oversized result to the driver.

Expected evidence:

- Driver or controller logs include driver OOM wording and a collect-pattern marker.
- Run context records client deploy mode unless explicitly overridden.

Expected recommendation:

- Remove large driver collects, write distributed outputs, or tune driver memory only after the code path is reviewed.

### `missing_dependency`

Starts Spark and imports a deliberately absent Python module.

Expected evidence:

- Driver logs contain `ModuleNotFoundError` or `No module named`.
- The missing module name is captured in the run context diagnostic signals.

Expected recommendation:

- Package the missing dependency with the job or add it to the EMR/bootstrap dependency path.

### `s3_access_denied`

Raises an S3 403-style failure against a demo-only path without changing shared IAM policy by default.

Expected evidence:

- Logs contain `AccessDenied while reading s3://...`.
- The denied S3 URI is present as the input path in exported context.

Expected recommendation:

- Review instance-profile permissions, bucket policy, object ownership, and encryption requirements for the specific prefix.

### `bad_input_data`

Uploads malformed demo CSV input and fails when schema validation finds invalid amount or timestamp fields.

Expected evidence:

- Spark logs contain `CSV malformed` or `schema mismatch`.
- Bad records live only under the demo raw bucket input prefix.

Expected recommendation:

- Add validation/quarantine handling and fix upstream parsing or input generation assumptions.

Advanced scenarios:

- `data_skew`
- `shuffle_spill`
- `long_running_data_delay`
- `long_running_resource_delay`
- `long_running_db_delay`
- `kms_access_denied`
- `hdfs_full`
- `db_connection_failure`
- `db_lock_timeout`
- `db_partition_hotspot`
- `db_large_join_spill`
- `db_bad_sql_plan`
- `glue_metastore_error`
- `livy_session_failure`
- `unknown_failure`

Run any advanced scenario with:

```bash
./scripts/run_scenario.sh data_skew
./scripts/run_scenario.sh shuffle_spill
./scripts/run_scenario.sh kms_access_denied
./scripts/run_scenario.sh hdfs_full
./scripts/run_scenario.sh db_connection_failure
./scripts/run_scenario.sh db_lock_timeout
./scripts/run_scenario.sh db_partition_hotspot
./scripts/run_scenario.sh db_large_join_spill
./scripts/run_scenario.sh db_bad_sql_plan
./scripts/run_scenario.sh glue_metastore_error
./scripts/run_scenario.sh livy_session_failure
./scripts/run_scenario.sh unknown_failure
```

`db_connection_failure`, `db_lock_timeout`, `glue_metastore_error`, `livy_session_failure`, and `unknown_failure` default to client deploy mode. Other advanced failures default to cluster mode. Set `DEPLOY_MODE=client` or `DEPLOY_MODE=cluster` to override either default.

Clean up a run with:

```bash
./scripts/cleanup_scenario.sh <scenario>
```

## Advanced Spark, IAM, Storage, And Livy Scenarios

### `data_skew`

Generates one hot key and many cold keys so Harrier can identify skew ratio, hot partition, and long-tail task evidence.

Expected evidence:

- Spark logs include data skew, skew ratio, hot partition, or long-tail task wording.
- Diagnostic signals include the generated skew ratio.

Expected recommendation:

- Repartition or salt skewed keys, filter earlier, tune shuffle partitions, or change join strategy.

### `shuffle_spill`

Runs a bounded wide aggregation and emits memory/disk spill evidence.

Expected evidence:

- Spark logs include shuffle spill, memory bytes spilled, or disk bytes spilled.
- Diagnostic signals include shuffle spill volume.

Expected recommendation:

- Tune shuffle partitions, executor memory overhead, and wide-stage data volume.

### `kms_access_denied`

Emits a safe KMS decrypt denial for an encrypted demo S3 path without changing KMS policy.

Expected evidence:

- Logs include `AccessDeniedException` and `kms:Decrypt`.
- Diagnostic signals include the encrypted input path and demo KMS key ARN.

Expected recommendation:

- Review key policy, S3 encryption settings, and least-privilege KMS grants for the EMR runtime role.

### `hdfs_full`

Simulates HDFS/local storage pressure without writing filler files.

Expected evidence:

- Logs include `No space left on device` or `local dirs are full`.
- Diagnostic signals include the local storage path.

Expected recommendation:

- Clean temporary data, increase storage capacity, and review shuffle spill or HDFS utilization.

### `livy_session_failure`

Produces client-mode Livy session failure evidence for session startup and batch submission failures.

Expected evidence:

- Step/controller/Livy-style logs include `Livy session failed`.
- Run context uses client deploy mode unless overridden.

Expected recommendation:

- Check Livy service health, session limits, Spark startup logs, and dependency bootstrap.

### `unknown_failure`

Emits a stable sentinel that does not match any deterministic Harrier classifier rule.

Expected evidence:

- Logs include `HarrierUnclassifiedDemoSignal`.
- No known classifier category should match the signal.

Expected recommendation:

- Keep the root cause as `UNKNOWN`.
- Return runbook-only guidance.
- Archive the finding if it recurs, then promote it into the rule system only after a stable signal, recommendation, MCP unit test, demo scenario, and expected findings exist.

## Long-Running Job Scenarios

These scenarios are investigated while the EMR step or YARN application is still running. The goal is to show that Harrier can explain delay before a terminal failure exists.

### `long_running_data_delay`

Simulates a job that is still running because one stage or a small set of tasks is processing disproportionate data.

Run:

```bash
HOT_PARTITION_SLEEP_SECONDS=900 ./scripts/run_scenario.sh long_running_data_delay
```

Expected evidence:

- EMR step and YARN application are still `RUNNING`.
- Spark stage/task evidence shows long-tail tasks, skewed input bytes, high shuffle spill, or oversized partitions.
- Driver/executor logs show progress but slow stage completion.

Expected recommendation:

- Repartition on a better key, salt skewed keys, pre-filter input, adjust shuffle partitions, or change join strategy.
- Prepare a PR with Spark code/config changes where the job repo is provided.

### `long_running_resource_delay`

Simulates a job that is still running because the cluster cannot provide enough resources.

Run:

```bash
EXECUTOR_INSTANCES=20 EXECUTOR_MEMORY=4g ./scripts/run_scenario.sh long_running_resource_delay
```

Expected evidence:

- EMR step and YARN application are still `RUNNING` or `ACCEPTED`.
- YARN or CloudWatch evidence shows pending containers, high memory/vCPU pressure, executor allocation churn, or node pressure.
- Spark logs show tasks waiting for executors or repeated executor loss/retry behavior.

Expected recommendation:

- Adjust executor sizing, dynamic allocation limits, memory overhead, partition count, or cluster capacity.
- Return runbook steps for capacity changes and PR-ready Spark config suggestions when applicable.

### `long_running_db_delay`

Simulates a Spark/JDBC job that is still running because database-side work is slow.

Run:

```bash
DB_SECRET_ID=demo/database/secret-id DB_SLEEP_SECONDS=900 ./scripts/run_scenario.sh long_running_db_delay
```

The secret should contain `jdbc_url`, `username`, and `password`. The job uses Secrets Manager so the demo does not put the database password in the EMR step arguments.

Expected evidence:

- Spark stage remains active while JDBC reads or writes continue.
- Read-only PostgreSQL diagnostics show an active long-running query, wait event, bad plan, large scan, or expensive join.
- Optional `EXPLAIN (FORMAT JSON)` evidence identifies the slow plan shape.

Expected recommendation:

- Improve JDBC bounds or partitioning, add predicate pushdown, rewrite the SQL, or propose reviewed index/statistics changes.
- Prepare a PR with SQL migration, rollback SQL, or Spark JDBC code/config changes where safe.

## DB Performance Scenarios

### `db_connection_failure`

Simulates a Spark/JDBC connection failure against an unreachable demo JDBC URL.

Run:

```bash
./scripts/run_scenario.sh db_connection_failure
```

Expected evidence:

- Driver logs include `PSQLException`, `JDBC`, and `connection refused`.
- Diagnostic signals include the JDBC URL host.

Expected recommendation:

- Validate endpoint, DNS, route, security group, credentials, and connection limits.

### `db_lock_timeout`

Simulates a PostgreSQL lock wait timeout. The helper `db/lock_simulator.py` can print matching local diagnostic evidence without connecting to a DB.

Run:

```bash
./scripts/run_scenario.sh db_lock_timeout
python3 db/lock_simulator.py
```

Expected evidence:

- Driver logs include lock timeout, waiting for lock, or blocked by pid.
- Optional simulator output matches the same evidence shape.

Expected recommendation:

- Use read-only DB diagnostics to identify blockers and review transaction scope or retry behavior.

### `db_partition_hotspot`

Simulates Spark reading or writing large chunks of relational data with poor partition bounds or too few JDBC partitions.

Expected evidence:

- Spark job uses JDBC with poor `partitionColumn`, `lowerBound`, `upperBound`, or `numPartitions`.
- One or a few Spark tasks process most of the data.
- PostgreSQL diagnostic queries show one dominant table/range or long-running query.

Expected recommendation:

- Fix JDBC partitioning options.
- Use a better partition column or bounded predicate pushdown.
- Consider DB-side table partitioning only as a reviewed migration.
- Prepare a PR with Spark config/code change and optional SQL migration note.

### `db_large_join_spill`

Simulates a large Spark-to-DB or DB-side join that spills, scans too much data, or misses a useful index.

Expected evidence:

- Spark logs show heavy shuffle/spill or slow JDBC stage.
- PostgreSQL diagnostics show sequential scan, hash join spill, missing index, or expensive join plan.
- Optional `EXPLAIN` output indicates the large join path.

Expected recommendation:

- Add or adjust an index via migration.
- Rewrite the join or pre-filter data before the join.
- Adjust Spark join strategy when the expensive work is on the Spark side.
- Prepare a PR with SQL migration and rollback SQL where safe.

### `db_bad_sql_plan`

Simulates a failed or clearly bad SQL execution plan for a query used by Spark/JDBC.

Expected evidence:

- Spark/JDBC stage is slow, fails, or times out while running a SQL query.
- Read-only PostgreSQL diagnostics capture active query text or query age.
- `EXPLAIN (FORMAT JSON)` or equivalent plan evidence shows a sequential scan over a large table, bad join order, nested loop over large inputs, missing index, stale statistics, or excessive sort/hash cost.
- Table/index metadata supports the diagnosis.

Expected recommendation:

- Add or adjust an index via reviewed migration.
- Rewrite the query to improve predicate pushdown or join shape.
- Add `ANALYZE`/statistics guidance as a validation step where stale stats are suspected.
- Prepare a PR with SQL migration, rollback SQL, and validation query.

### `glue_metastore_error`

Simulates a Spark job referencing a missing Glue Data Catalog or Hive metastore table.

Expected evidence:

- Driver logs include `Table or view not found`.
- Logs include an `EntityNotFoundException` for a table or database in Glue Data Catalog.
- No production table is read or modified.

Expected recommendation:

- Verify that the Glue database and table exist in the expected AWS region/account.
- Check that the EMR runtime role has the required Glue Data Catalog read permissions.
- If the job code references the wrong table, prepare a code PR that corrects the fully qualified table/database name.
