# Demo Overview

The demo lab creates controlled EMR on EC2 incidents and exports normal Harrier investigation context:

- AWS region
- EMR cluster ID
- EMR step ID
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
