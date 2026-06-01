# Demo Lab Examples

These examples are copyable entry points for running controlled Harrier demo
scenarios.

## EC2 Infra Scenario

```bash
SCENARIO=s3_access_denied RUNTIME=emr_ec2 make run-scenario
SCENARIO=s3_access_denied RUNTIME=emr_ec2 make validate
```

Expected finding: `S3_ACCESS_DENIED`.

## Serverless Data Scenario

```bash
SCENARIO=bad_input_data RUNTIME=emr_serverless make run-scenario
SCENARIO=bad_input_data RUNTIME=emr_serverless make validate
```

Expected finding: `BAD_INPUT_DATA`.

## EKS Kubernetes Scenario

```bash
SCENARIO=image_pull_failure RUNTIME=emr_eks make run-scenario
SCENARIO=image_pull_failure RUNTIME=emr_eks make validate
```

Expected finding: `EKS_IMAGE_PULL_FAILURE`.

