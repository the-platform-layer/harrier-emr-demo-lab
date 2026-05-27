# Harrier EMR Demo Lab

This repository contains the disposable demo environment for Harrier EMR MCP.

It owns demo infrastructure, Spark jobs, sample data, scenario runners, expected findings, validation scripts, alarms, cleanup, and cost controls.

The production MCP server and AWS DevOps Agent registration assets live in `harrier-emr-mcp`.

Track current build state in [PROGRESS.md](PROGRESS.md).

Track slice implementation tasks in [TASKS.md](TASKS.md).

## Drop 1 Demo Scope

- Amazon EMR on EC2
- S3 archived EMR logs
- CloudWatch metrics and alarms
- Controlled Spark failure scenarios
- Scenario validation against an already-running Harrier MCP endpoint

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

## Destroy

```bash
./scripts/destroy.sh
```

The destroy helper prints Terraform-managed resources and requires an explicit confirmation phrase.

## Cost Warning

The default cluster uses one primary node and one core node. EMR auto-termination is enabled after the configured idle period, but this is not a hard wall-clock cap if jobs keep the cluster busy.

Set up an AWS Budget or billing alarm for the demo account before long-running scenario work.
