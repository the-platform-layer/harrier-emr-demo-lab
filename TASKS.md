# Harrier EMR Demo Lab Task Plan

Use this file to implement the demo repo one slice at a time. Keep each slice independently testable and disposable.

## Slice 0: Bootstrap Demo Repo

Status: Done

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

Status: Not started

Goal: deploy a disposable EMR on EC2 demo cluster with logs enabled and cost controls.

Tasks:

- [ ] Add AWS provider configuration.
- [ ] Add common tags:
  - [ ] `Project=harrier-demo`
  - [ ] `Environment=demo`
- [ ] Add VPC.
- [ ] Add private/public subnets as needed.
- [ ] Add security groups.
- [ ] Add S3 raw bucket.
- [ ] Add S3 processed bucket.
- [ ] Add S3 EMR logs bucket.
- [ ] Add S3 lifecycle rules.
- [ ] Add EMR service role.
- [ ] Add EMR EC2 instance profile.
- [ ] Add EMR on EC2 cluster.
- [ ] Install Spark.
- [ ] Install Livy.
- [ ] Enable S3 logging.
- [ ] Add EMR auto-termination policy.
- [ ] Add CloudWatch log retention.
- [ ] Add alarm placeholders.
- [ ] Keep RDS disabled by default.
- [ ] Add optional cost alarm or document AWS Budget setup.
- [ ] Add Terraform outputs:
  - [ ] `cluster_id`
  - [ ] `log_uri`
  - [ ] `raw_bucket`
  - [ ] `processed_bucket`
  - [ ] `region`
  - [ ] `max_runtime_hours`
- [ ] Update `docs/cost-and-retention.md`.
- [ ] Update `README.md` with deploy and cleanup notes.

Done when:

- [ ] `terraform validate` passes.
- [ ] Terraform can produce a plan.
- [ ] All resources are clearly prefixed/tagged as demo.
- [ ] Cost and cleanup instructions are documented.

## Slice 3: Happy Path Spark Job

Status: Not started

Goal: create a known-good Spark job to prove the demo environment works.

Tasks:

- [ ] Implement sample data generator in `scripts/generate_data.py`.
- [ ] Implement `spark-jobs/happy_path/job.py`.
- [ ] Read raw data from S3.
- [ ] Aggregate sample data.
- [ ] Write processed output to S3.
- [ ] Implement `scripts/submit_step.sh`.
- [ ] Implement `scripts/export_investigation_context.sh`.
- [ ] Extract cluster ID.
- [ ] Extract step ID.
- [ ] Extract YARN application ID where available.
- [ ] Export region and time window.
- [ ] Update `docs/demo-overview.md`.
- [ ] Update `docs/scenarios.md`.

Done when:

- [ ] Sample data is generated.
- [ ] Spark job can be submitted as an EMR step.
- [ ] Output lands in processed S3 bucket.
- [ ] EMR logs are available.
- [ ] Investigation context JSON is exported.

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
- [ ] Each scenario has expected finding JSON.
- [ ] Cleanup restores demo state.
- [ ] Harrier can detect each scenario through normal investigation context.

## Slice 14: Demo Scenarios Batch 2

Status: Not started

Goal: implement advanced demo scenarios.

Scenarios:

- `data_skew`
- `shuffle_spill`
- `kms_access_denied`
- `hdfs_full`
- `db_connection_failure`
- `db_lock_timeout`
- `livy_session_failure`

Tasks for each scenario:

- [ ] Implement job or simulator.
- [ ] Add scenario config if needed.
- [ ] Add `run_scenario.sh` entry.
- [ ] Add expected finding JSON.
- [ ] Add cleanup behavior.
- [ ] Document how to run.
- [ ] Document expected evidence.

Scenario-specific tasks:

- [ ] `data_skew`: generate skewed keys and long-tail task evidence.
- [ ] `shuffle_spill`: generate heavy shuffle/spill evidence.
- [ ] `kms_access_denied`: configure demo KMS denial safely.
- [ ] `hdfs_full`: simulate storage pressure safely.
- [ ] `db_connection_failure`: enable optional PostgreSQL demo path.
- [ ] `db_lock_timeout`: add safe lock simulator.
- [ ] `livy_session_failure`: produce Livy session failure evidence.

Done when:

- [ ] Each scenario is reproducible.
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

