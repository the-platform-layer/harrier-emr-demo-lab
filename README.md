# Harrier EMR Demo Lab

This repository contains the disposable demo environment for Harrier EMR MCP.

It owns demo infrastructure, Spark jobs, sample data, scenario runners, expected findings, validation scripts, alarms, cleanup, and cost controls.

The production MCP server and AWS DevOps Agent registration assets live in `harrier-emr-mcp`.

## Drop 1 Demo Scope

- Amazon EMR on EC2
- Amazon EMR Serverless Spark application for the Slice 30 demo scenarios
- EMR on EKS virtual cluster registration for Slice 31 scenarios
- S3 archived EMR logs
- CloudWatch metrics and alarms
- Controlled Spark failure scenarios
- Scenario validation against an already-running Harrier MCP endpoint
- Optional AWS MWAA-compatible local runner on ECS Fargate for scenario orchestration

## Safety

Demo resources are disposable. Use a demo AWS account when possible.

Defaults to implement in Terraform:

- `Project=harrier-demo` and `Environment=demo` tags
- EMR auto-termination
- S3 lifecycle rules
- CloudWatch log retention
- Optional cost alarm or AWS Budget setup
- Cleanup scripts per scenario

## Deploy Baseline Infrastructure

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

Or use the helper:

```bash
./scripts/deploy.sh
```

Key outputs:

- `cluster_id`
- `log_uri`
- `raw_bucket`
- `processed_bucket`
- `region`
- `max_runtime_hours`
- `emr_serverless_application_id`
- `emr_serverless_job_role_arn`
- `emr_serverless_log_uri`
- `emr_eks_virtual_cluster_id`
- `emr_eks_job_role_arn`
- `emr_eks_log_uri`

## Run EMR Serverless Scenarios

Slice 30 adds a parallel Serverless runtime for the simpler Spark scenarios:

```bash
RUNTIME=emr_serverless ./scripts/run_scenario.sh happy_path
RUNTIME=emr_serverless ./scripts/run_scenario.sh executor_oom
RUNTIME=emr_serverless ./scripts/run_scenario.sh missing_dependency
RUNTIME=emr_serverless ./scripts/run_scenario.sh s3_path_missing
RUNTIME=emr_serverless ./scripts/run_scenario.sh bad_input_data
```

The Serverless submitter uploads the PySpark entry point, starts an EMR Serverless job run, enables S3 and CloudWatch log publication, and writes `.harrier-demo/last-context.json` with `runtime=emr_serverless`, `target.serverless_application_id`, and `target.job_run_id`.

Validate through Harrier with the same harness:

```bash
AWS_ACCOUNT_ID=123456789012 \
RUNTIME=emr_serverless \
./scripts/validate_scenario.sh executor_oom
```

## Run EMR On EKS Scenarios

Slice 31 targets an existing EKS cluster. Prepare the namespace and EMR job role trust first:

```bash
EMR_EKS_CLUSTER_NAME=analytics-dev \
EMR_EKS_JOB_ROLE_ARN=arn:aws:iam::123456789012:role/harrier-demo-emr-eks-job \
./scripts/setup_eks_virtual_cluster.sh
```

Then enable virtual-cluster registration in Terraform:

```bash
terraform -chdir=infra/terraform apply \
  -var enable_emr_eks=true \
  -var emr_eks_cluster_name=analytics-dev \
  -var emr_eks_namespace=harrier-emr-jobs \
  -var emr_eks_job_role_arn=arn:aws:iam::123456789012:role/harrier-demo-emr-eks-job
```

Run the EKS scenarios:

```bash
RUNTIME=emr_eks ./scripts/run_scenario.sh happy_path
RUNTIME=emr_eks ./scripts/run_scenario.sh executor_oom
RUNTIME=emr_eks ./scripts/run_scenario.sh image_pull_failure
RUNTIME=emr_eks ./scripts/run_scenario.sh pod_pending_resource_pressure
RUNTIME=emr_eks ./scripts/run_scenario.sh s3_access_denied
```

The EKS submitter uploads the PySpark entry point, starts an EMR Containers job run, enables S3 and CloudWatch log publication, and writes `.harrier-demo/last-context.json` with `runtime=emr_eks`, `target.virtual_cluster_id`, `target.job_run_id`, `target.eks_cluster_name`, and `target.namespace`.

Validate through Harrier:

```bash
AWS_ACCOUNT_ID=123456789012 \
RUNTIME=emr_eks \
./scripts/validate_scenario.sh image_pull_failure
```

Prerequisites are documented in [docs/emr-on-eks-prerequisites.md](docs/emr-on-eks-prerequisites.md).

## Run Happy Path

After the baseline cluster exists, submit the known-good Spark job:

```bash
./scripts/run_scenario.sh happy_path
```

The script generates deterministic CSV input, uploads it to the raw S3 bucket, uploads the PySpark job, submits an EMR step, and writes the latest context to `.harrier-demo/last-context.json`.

Use `DEPLOY_MODE=client` or `DEPLOY_MODE=cluster` to choose the Spark driver log layout for a run. Cluster mode is the default.

Export the Harrier investigation context:

```bash
./scripts/export_investigation_context.sh
```

The exporter preserves cluster ID, step ID, deploy mode, job state, region, S3 paths, and time window. When EMR step logs are available in S3, it also tries to extract the YARN application ID.

Long-running delay demos can be submitted the same way:

```bash
./scripts/run_scenario.sh long_running_data_delay
./scripts/run_scenario.sh long_running_resource_delay
DB_SECRET_ID=<secret-id> ./scripts/run_scenario.sh long_running_db_delay
```

These runs keep the EMR step in a running window so Harrier can investigate delay before failure.

Slice 10 controlled failure demos:

```bash
./scripts/run_scenario.sh executor_oom
./scripts/run_scenario.sh driver_oom
./scripts/run_scenario.sh missing_dependency
./scripts/run_scenario.sh s3_access_denied
./scripts/run_scenario.sh bad_input_data
```

The runner writes context to `.harrier-demo/last-context.json` for each run. Use `./scripts/cleanup_scenario.sh <scenario>` to remove demo S3 artifacts and cancel an active step when possible.

Slice 14 advanced demos:

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
./scripts/run_scenario.sh livy_session_failure
```

The DB and Livy failure scenarios are safe simulations by default. They emit diagnostic evidence without mutating a database, KMS policy, IAM policy, Livy server, HDFS, or local disks.

## Run Scenarios From MWAA Local Runner On ECS

The demo lab includes an AWS MWAA-compatible local runner container deployment for ECS Fargate. It uses AWS's `aws/aws-mwaa-local-runner` image source and layers in the Harrier DAGs and scenario scripts.

```bash
./scripts/deploy_mwaa_local_runner.sh
```

After deploy:

```bash
terraform -chdir=infra/terraform output mwaa_airflow_url
terraform -chdir=infra/terraform output mwaa_admin_password_secret_arn
```

Open the Airflow UI, log in as `admin`, and trigger `harrier_demo_run_scenario` or `harrier_demo_smoke_suite`.

Details are in [docs/mwaa-local-runner.md](docs/mwaa-local-runner.md).

## Destroy

```bash
./scripts/destroy.sh
```

The destroy helper prints Terraform-managed resources and requires an explicit confirmation phrase.

## Cost Warning

The default cluster uses one primary node and one core node. EMR auto-termination is enabled after the configured idle period, but this is not a hard wall-clock cap if jobs keep the cluster busy.

Set up an AWS Budget or billing alarm for the demo account before long-running scenario work.
