# Demo Overview

The demo lab creates controlled EMR on EC2 incidents and exports normal Harrier investigation context:

- AWS region
- EMR cluster ID
- EMR step ID
- job state where known
- YARN application ID where available
- Failure time window

The demo lab does not host or deploy the production MCP server.

## Baseline Infrastructure

Slice 2 creates the disposable EMR on EC2 baseline:

- VPC and public subnet
- raw, processed, and EMR logs S3 buckets
- EMR service role and EC2 instance profile
- EMR cluster with Spark and Livy
- S3 log archive path
- CloudWatch alarms with actions disabled
- lifecycle and retention controls

Use Terraform outputs from `infra/terraform` as the source of truth for cluster and bucket identifiers.

## Happy Path

Slice 3 adds a known-good Spark job that proves the baseline cluster can run a normal job before failure scenarios are introduced.

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
