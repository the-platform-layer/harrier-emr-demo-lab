# Demo Overview

The demo lab creates controlled EMR incidents and exports normal Harrier investigation context. It currently supports EMR on EC2, a focused EMR Serverless scenario set, and an EMR on EKS scenario set for an existing EKS cluster.

- AWS region
- runtime
- runtime-specific target IDs
- job state where known
- YARN application ID where available
- EMR Serverless application ID and job run ID where applicable
- EMR on EKS virtual cluster ID, job run ID, EKS cluster name, and namespace where applicable
- Failure time window

The demo lab does not host or deploy the production MCP server.

## Baseline Infrastructure

The disposable EMR on EC2 baseline includes:

- VPC and public subnet
- raw, processed, and EMR logs S3 buckets
- EMR service role and EC2 instance profile
- EMR cluster with Spark and Livy
- S3 log archive path
- CloudWatch alarms with actions disabled
- lifecycle and retention controls

Use Terraform outputs from `infra/terraform` as the source of truth for cluster and bucket identifiers.

The disposable EMR Serverless baseline includes:

- EMR Serverless Spark application
- EMR Serverless job execution role
- S3 monitoring log URI under the demo logs bucket
- CloudWatch log group for driver and executor stdout/stderr
- auto-start and auto-stop settings so no workers remain active after idle timeout

The EMR on EKS setup can register an existing EKS cluster:

- CloudWatch log group for EMR Containers driver, executor, and submitter logs
- optional `aws_emrcontainers_virtual_cluster` registration for a supplied EKS cluster and namespace
- setup helper for namespace creation, EMR Containers access mapping, and job-role trust updates
- job submitter for happy path, executor OOM, image pull failure, pod pending/resource pressure, and S3 access denied

## Happy Path

The happy path scenario proves the baseline cluster can run a normal job before
failure scenarios are introduced.

The happy path flow is:

1. `scripts/generate_data.py` creates deterministic event CSV data.
2. `scripts/submit_step.sh` uploads input data to the raw S3 bucket.
3. `scripts/submit_step.sh` uploads `spark-jobs/happy_path/job.py` to S3.
4. EMR runs the job through `spark-submit`.
5. The job writes daily country aggregates and event type summaries to the processed S3 bucket.
6. `.harrier-demo/last-context.json` records investigation context for Harrier.

Run it with:

```bash
./scripts/run_scenario.sh happy_path
```

Export context with:

```bash
./scripts/export_investigation_context.sh
```

## Deploy Mode Coverage

Spark client mode and cluster mode produce different driver log layouts. Demo runs should capture deploy mode in exported investigation context:

```json
{
  "deploy_mode": "client"
}
```

or:

```json
{
  "deploy_mode": "cluster"
}
```

At minimum, the demo set should validate:

- a cluster-mode scenario where driver logs are under YARN/container logs
- a client-mode scenario where driver logs are under step/controller/Livy/primary-node logs
- a Serverless scenario where driver and executor logs are discovered from Serverless S3 or CloudWatch layouts
- an EKS scenario where driver, executor, submitter, and Kubernetes pod status evidence are available when the cluster API can be read
