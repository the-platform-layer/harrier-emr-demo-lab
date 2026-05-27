# Harrier EMR Demo Lab Task Plan

Use this file to implement the demo repo one slice at a time. Keep each slice independently testable and disposable.

## Slice 0: Bootstrap Demo Repo

Status: Implemented, pending live AWS verification

Tasks:

- [x] Create Terraform folder.
- [x] Create Spark jobs folder.
- [x] Create scenario docs.
- [x] Create scripts folder.
- [x] Create expected findings folder.
- [x] Create cost and retention docs.
- [x] Create placeholder validation workflow.
- [x] Confirm no production MCP server code or MCP deployment infrastructure lives in this repo.

Done when:

- [x] Repo has an initial commit on `main`.
- [x] Repo has `PROGRESS.md` and `TASKS.md`.
- [x] Local working tree is clean.

## Slice 2: Demo EMR Baseline Infrastructure

Status: Implemented, pending live AWS verification

Goal: deploy a disposable EMR on EC2 demo cluster with logs enabled and cost controls.

Tasks:

- [x] Add AWS provider configuration.
- [x] Add common tags:
  - [x] `Project=harrier-demo`
  - [x] `Environment=demo`
- [x] Add VPC.
- [x] Add private/public subnets as needed.
- [x] Add security groups.
- [x] Add S3 raw bucket.
- [x] Add S3 processed bucket.
- [x] Add S3 EMR logs bucket.
- [x] Add S3 lifecycle rules.
- [x] Add EMR service role.
- [x] Add EMR EC2 instance profile.
- [x] Add EMR on EC2 cluster.
- [x] Install Spark.
- [x] Install Livy.
- [x] Enable S3 logging.
- [x] Add EMR auto-termination policy.
- [x] Add CloudWatch log retention.
- [x] Add alarm placeholders.
- [x] Keep RDS disabled by default.
- [x] Add optional cost alarm or document AWS Budget setup.
- [x] Add Terraform outputs:
  - [x] `cluster_id`
  - [x] `log_uri`
  - [x] `raw_bucket`
  - [x] `processed_bucket`
  - [x] `region`
  - [x] `max_runtime_hours`
- [x] Update `docs/cost-and-retention.md`.
- [x] Update `README.md` with deploy and cleanup notes.

Done when:

- [x] `terraform validate` passes.
- [x] Terraform can produce a plan.
- [x] All resources are clearly prefixed/tagged as demo.
- [x] Cost and cleanup instructions are documented.

## Slice 3: Happy Path Spark Job

Status: Done

Goal: create a known-good Spark job to prove the demo environment works.

Tasks:

- [x] Implement sample data generator in `scripts/generate_data.py`.
- [x] Implement `spark-jobs/happy_path/job.py`.
- [x] Read raw data from S3.
- [x] Aggregate sample data.
- [x] Write processed output to S3.
- [x] Implement `scripts/submit_step.sh`.
- [x] Implement `scripts/export_investigation_context.sh`.
- [x] Extract cluster ID.
- [x] Extract step ID.
- [x] Export `deploy_mode` as `client`, `cluster`, or `unknown`.
- [x] Extract YARN application ID where available.
- [x] Export region and time window.
- [x] Update `docs/demo-overview.md`.
- [x] Update `docs/scenarios.md`.

Done when:

- [x] Sample data is generated.
- [x] Spark job can be submitted as an EMR step.
- [ ] Output lands in processed S3 bucket.
- [ ] EMR logs are available.
- [x] Investigation context JSON is exported.

## Slice 10: Demo Scenarios Batch 1

Status: Not started

Goal: implement the first five controlled failure scenarios.

Scenarios:

- `executor_oom`
- `driver_oom`
- `missing_dependency`
- `s3_access_denied`
- `bad_input_data`

Tasks for each scenario:

- [ ] Implement PySpark job.
- [ ] Add scenario config if needed.
- [ ] Mark each scenario with intended Spark deploy mode.
- [ ] Add `run_scenario.sh` entry.
- [ ] Add expected finding JSON.
- [ ] Add cleanup behavior.
- [ ] Document how to run.
- [ ] Document expected Harrier result.
- [ ] Keep data and permissions isolated to demo resources.

Scenario-specific tasks:

- [ ] `executor_oom`: produce YARN/container memory kill evidence.
- [ ] `driver_oom`: produce driver memory/code-pattern evidence.
- [ ] `missing_dependency`: produce missing Python/JVM dependency evidence.
- [ ] `s3_access_denied`: produce S3 AccessDenied evidence with demo-only path.
- [ ] `bad_input_data`: produce corrupt/schema mismatch evidence.

Done when:

- [ ] Each scenario is runnable.
- [ ] Each scenario creates expected logs.
- [ ] Batch 1 includes at least one client-mode and one cluster-mode log layout.
- [ ] Each scenario has expected finding JSON.
- [ ] Cleanup restores demo state.
- [ ] Harrier can detect each scenario through normal investigation context.

## Slice 14: Demo Scenarios Batch 2

Status: Not started

Goal: implement advanced demo scenarios.

Scenarios:

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

Tasks for each scenario:

- [ ] Implement job or simulator.
- [ ] Add scenario config if needed.
- [ ] Mark each scenario with intended Spark deploy mode.
- [ ] Add `run_scenario.sh` entry.
- [ ] Add expected finding JSON.
- [ ] Add cleanup behavior.
- [ ] Document how to run.
- [ ] Document expected evidence.

Scenario-specific tasks:

- [ ] `data_skew`: generate skewed keys and long-tail task evidence.
- [ ] `shuffle_spill`: generate heavy shuffle/spill evidence.
- [ ] `long_running_data_delay`: leave a Spark job running long enough to show active stage/task skew, spill, or oversized partition evidence before failure.
- [ ] `long_running_resource_delay`: leave a Spark job running with pending containers, saturated executors, or cluster capacity pressure before failure.
- [ ] `long_running_db_delay`: leave a Spark/JDBC job running while read-only DB diagnostics show active query wait, bad plan, or large scan/join delay.
- [ ] `kms_access_denied`: configure demo KMS denial safely.
- [ ] `hdfs_full`: simulate storage pressure safely.
- [ ] `db_connection_failure`: enable optional PostgreSQL demo path.
- [ ] `db_lock_timeout`: add safe lock simulator.
- [ ] `db_partition_hotspot`: simulate poor JDBC partitioning over large DB chunks.
- [ ] `db_large_join_spill`: simulate expensive large join / missing index diagnostics.
- [ ] `db_bad_sql_plan`: simulate a failed or inefficient SQL plan used by Spark/JDBC.
- [ ] `livy_session_failure`: produce Livy session failure evidence.

DB performance scenario tasks:

- [ ] Add seed data large enough to make partitioning/join behavior visible but still demo-safe.
- [ ] Add PostgreSQL diagnostic SQL for read-only troubleshooting.
- [ ] Add running DB query capture path for `long_running_db_delay`.
- [ ] Add optional migration SQL examples for recommended fixes.
- [ ] Add rollback SQL examples where applicable.
- [ ] Add an `EXPLAIN (FORMAT JSON)` capture path for `db_bad_sql_plan`.
- [ ] Ensure MCP recommendations are PR suggestions only and never direct DB changes.

Done when:

- [ ] Each scenario is reproducible.
- [ ] Advanced scenarios include both client-mode and cluster-mode log layout coverage.
- [ ] Each scenario has expected finding JSON.
- [ ] Cleanup restores demo state.
- [ ] Harrier detects each scenario or records known evidence gaps.

## Slice 19: Scenario Validation Harness

Status: Started

Goal: automate regression testing for Harrier against demo scenarios.

Tasks:

- [ ] Implement `scripts/validate_scenario.sh`.
- [ ] Accept scenario name as input.
- [ ] Run selected scenario.
- [ ] Export investigation context JSON.
- [ ] Invoke already-running Harrier MCP endpoint.
- [ ] Capture Harrier result.
- [ ] Load `expected-findings/<scenario>.json`.
- [ ] Compare actual root cause category to expected category.
- [ ] Print pass/fail summary.
- [ ] Write validation report JSON.
- [ ] Add failure output useful for debugging.
- [ ] Document required environment variables.
- [ ] Update `docs/expected-findings.md`.

Done when:

- [ ] Harness can run locally against a configured demo AWS account.
- [ ] Harness does not deploy or host the MCP server.
- [ ] Harness output is deterministic enough for regression tracking.
