# Scenarios

Every Spark scenario should record the deploy mode used by the run:

```text
client
cluster
```

This matters because driver logs land in different places:

- cluster mode: driver logs are usually YARN/container logs.
- client mode: driver logs are usually step/controller/Livy/primary-node logs.

The demo lab should include at least one client-mode and one cluster-mode run before the first public demo.

Initial scenario set:

- `happy_path`
- `executor_oom`
- `driver_oom`
- `missing_dependency`
- `s3_access_denied`
- `bad_input_data`

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
- `livy_session_failure`

## Long-Running Job Scenarios

These scenarios are investigated while the EMR step or YARN application is still running. The goal is to show that Harrier can explain delay before a terminal failure exists.

### `long_running_data_delay`

Simulates a job that is still running because one stage or a small set of tasks is processing disproportionate data.

Expected evidence:

- EMR step and YARN application are still `RUNNING`.
- Spark stage/task evidence shows long-tail tasks, skewed input bytes, high shuffle spill, or oversized partitions.
- Driver/executor logs show progress but slow stage completion.

Expected recommendation:

- Repartition on a better key, salt skewed keys, pre-filter input, adjust shuffle partitions, or change join strategy.
- Prepare a PR with Spark code/config changes where the job repo is provided.

### `long_running_resource_delay`

Simulates a job that is still running because the cluster cannot provide enough resources.

Expected evidence:

- EMR step and YARN application are still `RUNNING` or `ACCEPTED`.
- YARN or CloudWatch evidence shows pending containers, high memory/vCPU pressure, executor allocation churn, or node pressure.
- Spark logs show tasks waiting for executors or repeated executor loss/retry behavior.

Expected recommendation:

- Adjust executor sizing, dynamic allocation limits, memory overhead, partition count, or cluster capacity.
- Return runbook steps for capacity changes and PR-ready Spark config suggestions when applicable.

### `long_running_db_delay`

Simulates a Spark/JDBC job that is still running because database-side work is slow.

Expected evidence:

- Spark stage remains active while JDBC reads or writes continue.
- Read-only PostgreSQL diagnostics show an active long-running query, wait event, bad plan, large scan, or expensive join.
- Optional `EXPLAIN (FORMAT JSON)` evidence identifies the slow plan shape.

Expected recommendation:

- Improve JDBC bounds or partitioning, add predicate pushdown, rewrite the SQL, or propose reviewed index/statistics changes.
- Prepare a PR with SQL migration, rollback SQL, or Spark JDBC code/config changes where safe.

## DB Performance Scenarios

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
