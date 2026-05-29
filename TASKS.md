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

Status: Implemented

Goal: implement the first five controlled failure scenarios.

Scenarios:

- `executor_oom`
- `driver_oom`
- `missing_dependency`
- `s3_access_denied`
- `bad_input_data`

Tasks for each scenario:

- [x] Implement PySpark job.
- [x] Add scenario config if needed.
- [x] Mark each scenario with intended Spark deploy mode.
- [x] Add `run_scenario.sh` entry.
- [x] Add expected finding JSON.
- [x] Add cleanup behavior.
- [x] Document how to run.
- [x] Document expected Harrier result.
- [x] Keep data and permissions isolated to demo resources.

Scenario-specific tasks:

- [x] `executor_oom`: produce YARN/container memory kill evidence.
- [x] `driver_oom`: produce driver memory/code-pattern evidence.
- [x] `missing_dependency`: produce missing Python/JVM dependency evidence.
- [x] `s3_access_denied`: produce S3 AccessDenied evidence with demo-only path.
- [x] `bad_input_data`: produce corrupt/schema mismatch evidence.

Done when:

- [x] Each scenario is runnable.

## Slice 20: MWAA Local Runner On ECS

Status: Implemented, pending live ECS verification

Goal: run demo scenario orchestration from an AWS MWAA-compatible local runner container on ECS Fargate.

Tasks:

- [x] Use AWS `aws/aws-mwaa-local-runner` as the base image source.
- [x] Add Harrier Airflow DAGs.
- [x] Add a manual single-scenario DAG.
- [x] Add a smoke-suite DAG.
- [x] Reuse existing scenario runner scripts.
- [x] Upload Airflow scenario context JSON to S3 logs bucket.
- [x] Add custom image build script.
- [x] Add deploy helper that builds, pushes, and applies Terraform.
- [x] Add ECR repository for the MWAA local runner image.
- [x] Add ECS cluster, task definition, service, ALB, and target group.
- [x] Add task execution role and task role.
- [x] Pass demo EMR/S3 outputs into the Airflow container.
- [x] Store Airflow admin password in Secrets Manager.
- [x] Document deployment, login, DAGs, and cost controls.

Done when:

- [x] DAG files compile locally.
- [x] Terraform validates.
- [ ] Image is built and pushed to ECR.
- [ ] ECS service reaches steady state with `mwaa_desired_count=1`.
- [ ] Airflow UI is reachable.
- [ ] `harrier_demo_run_scenario` can submit `happy_path`.
- [x] Each scenario creates expected logs.
- [x] Batch 1 includes at least one client-mode and one cluster-mode log layout.
- [x] Each scenario has expected finding JSON.
- [x] Cleanup restores demo state.
- [x] Harrier can detect each scenario through normal investigation context.

## Slice 14: Demo Scenarios Batch 2

Status: Implemented

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

- [x] Implement job or simulator.
- [x] Add scenario config if needed.
- [x] Mark each scenario with intended Spark deploy mode.
- [x] Add `run_scenario.sh` entry.
- [x] Add expected finding JSON.
- [x] Add cleanup behavior.
- [x] Document how to run.
- [x] Document expected evidence.

Scenario-specific tasks:

- [x] `data_skew`: generate skewed keys and long-tail task evidence.
- [x] `shuffle_spill`: generate heavy shuffle/spill evidence.
- [x] `long_running_data_delay`: leave a Spark job running long enough to show active stage/task skew, spill, or oversized partition evidence before failure.
- [x] `long_running_resource_delay`: leave a Spark job running with pending containers, saturated executors, or cluster capacity pressure before failure.
- [x] `long_running_db_delay`: leave a Spark/JDBC job running while read-only DB diagnostics show active query wait, bad plan, or large scan/join delay.
- [x] `kms_access_denied`: configure demo KMS denial safely.
- [x] `hdfs_full`: simulate storage pressure safely.
- [x] `db_connection_failure`: enable optional PostgreSQL demo path.
- [x] `db_lock_timeout`: add safe lock simulator.
- [x] `db_partition_hotspot`: simulate poor JDBC partitioning over large DB chunks.
- [x] `db_large_join_spill`: simulate expensive large join / missing index diagnostics.
- [x] `db_bad_sql_plan`: simulate a failed or inefficient SQL plan used by Spark/JDBC.
- [x] `livy_session_failure`: produce Livy session failure evidence.

DB performance scenario tasks:

- [x] Add seed data large enough to make partitioning/join behavior visible but still demo-safe.
- [x] Add PostgreSQL diagnostic SQL for read-only troubleshooting.
- [x] Add running DB query capture path for `long_running_db_delay`.
- [x] Add optional migration SQL examples for recommended fixes.
- [x] Add rollback SQL examples where applicable.
- [x] Add an `EXPLAIN (FORMAT JSON)` capture path for `db_bad_sql_plan`.
- [x] Ensure MCP recommendations are PR suggestions only and never direct DB changes.

Done when:

- [x] Each scenario is reproducible.
- [x] Advanced scenarios include both client-mode and cluster-mode log layout coverage.
- [x] Each scenario has expected finding JSON.
- [x] Cleanup restores demo state.
- [x] Harrier detects each scenario or records known evidence gaps.

## Slice 19: Scenario Validation Harness

Status: Done

Goal: automate regression testing for Harrier against demo scenarios.

Tasks:

- [x] Implement `scripts/validate_scenario.sh` (thin wrapper around `validation/validate.py`).
- [x] Accept scenario name as input.
- [x] Run selected scenario (via `scripts/run_scenario.sh`; skippable with `SKIP_SCENARIO_RUN=1`).
- [x] Export investigation context JSON (via `scripts/export_investigation_context.sh`).
- [x] Invoke already-running Harrier MCP endpoint (MCP Streamable HTTP client in `validation/harrier_client.py`).
- [x] Capture Harrier result.
- [x] Load `expected-findings/<scenario>.json`.
- [x] Compare actual root cause category to expected category.
- [x] Check recommendation_type and pr_ready when present in expected findings.
- [x] Print pass/fail summary.
- [x] Write validation report JSON to `.harrier-demo/validation/<scenario>-<ts>.json`.
- [x] Add failure output useful for debugging (per-check messages, expected vs actual).
- [x] Document required environment variables (HARRIER_MCP_URL, AWS_ACCOUNT_ID, SKIP_SCENARIO_RUN).
- [x] Implement `validation/compare.py` with ValidationCheck and ComparisonResult dataclasses.
- [x] Implement `validation/report.py` with format_report and write_report.
- [x] Add 83 unit tests in `tests/test_slice19_harness.py`; all pass without live AWS or MCP calls.

Done when:

- [x] Harness can run locally against a configured demo AWS account.
- [x] Harness does not deploy or host the MCP server.
- [x] Harness output is deterministic enough for regression tracking.
