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

## Destroy

```bash
./scripts/destroy.sh
```

The destroy helper prints Terraform-managed resources and requires an explicit confirmation phrase.

## Cost Warning

The default cluster uses one primary node and one core node. EMR auto-termination is enabled after the configured idle period, but this is not a hard wall-clock cap if jobs keep the cluster busy.

Set up an AWS Budget or billing alarm for the demo account before long-running scenario work.
